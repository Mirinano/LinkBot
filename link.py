#!python3.8
import os, sys, glob
import time, datetime
import requests, json
import re
import asyncio, aiohttp
import discord #1.3.2
from discord import Webhook, AsyncWebhookAdapter
import sqlite3
import sql_format

from __init__ import Config as config
from __init__ import Error as error
from __init__ import BotMessage as bm

class Link():
    def __init__(self, client):
        self.client = client
        self.connect_db()

    def connect_db(self):
        self.conn = sqlite3.connect(config.DB, isolation_level=None) #auto commit
    
    async def boot(self):
        self.mas_server  = self.client.get_guild(config.MAS_SERVER)
        self.mas_channel = self.client.get_channel(config.MAS_CHANNEL)
        self.mas_category= self.client.get_channel(config.MAS_CATEGORY)

    async def main(self, msg:discord.Message):
        #blacklist
        if self.black_list(msg.author.id):
            return None
        unit = self.search_unit(msg)
        if unit is None:
            return #not unit link channel
        self.insert_messages(msg, unit) #insert message DB
        if msg.webhook_id is not None:
            #message send by webhook
            return None
        content = self.create_content(msg)
        urls = self.choice_send_webhooks(unit, msg.channel.id)
        for ch_id, url in urls:
            send_msg = await self.send(url, wait=True, **content)
            self.insert_unit_message(unit, msg.id, send_msg.id)
        em = self.master_log_embed(msg)
        if content.get("embeds") is None:
            content["embeds"] = [em]
        else:
            content["embeds"].append(em)
        #send master server
        await self.send(self.master_webhook_by_unit(unit), **content)
        
    def master_log_embed(self, msg:discord.Message) -> discord.Embed:
        em = discord.Embed(
            description="[{0}]({1})".format(str(msg.id), msg.jump_url)
        )
        return em

    def search_unit(self, msg:discord.Message) -> str:
        ch_id = msg.channel.id
        c = self.conn.execute(
            sql_format.select_unit_by_channel.format(ch_id)
        )
        for row in c:
            return row[1]
        return None

    def create_content(self, msg:discord.message) -> dict:
        data = {
            "username" : "{}[{}]".format(msg.author.name, msg.channel.guild.name),
            "avatar_url" : msg.author.avatar_url,
            "content" : self.invalid_mention(msg)
        }
        if len(msg.attachments) > 0:
            data["embeds"] = list()
            for attach in msg.attachments:
                em = discord.Embed()
                em.set_image(url=attach.url)
                data["embeds"].append(em)
        return data
    
    def invalid_mention(self, msg:discord.Message) -> str:
        text = msg.content
        #@everyone, @here
        text = text.replace("@everyone", "`@everyone`")
        text = text.replace("@here", "`@here`")
        for member in msg.mentions:
            text = text.replace("<@!{}>".format(member.id), member.name)
        return text

    def create_join_content(self, server:discord.Guild, unit:str, servers:list) -> dict:
        data = {
            "username" : server.name,
            "avatar_url" : server.icon_url,
            "content" : bm.join_msg.format(
                join = server.name,
                unit = unit,
                servers = ", ".join(servers)
            )
        }
        return data
    
    def create_left_content(self, server:discord.Guild, unit:str, servers:list) -> dict:
        data = {
            "username" : server.name,
            "avatar_url" : server.icon_url,
            "content" : bm.left_msg.format(
                left = server.name,
                unit = unit,
                servers = ", ".join(servers)
            )
        }
        return data
    
    def create_group_list_content(self, unit:str, servers:list) -> str:
        return bm.group_list_msg.format(
            unit = unit,
            servers = "\n\t".join(servers)
        )

    def choice_send_webhooks(self, unit:str, ch_id:int) -> list:
        c = self.conn.execute(
            sql_format.choice_send_webhook.format(
                unit=unit,
                channel=ch_id
            )
        )
        return [(r[0], r[2]) for r in c]

    def insert_messages(self, msg:discord.Message, unit:str) -> bool:
        self.conn.execute(
            sql_format.insert_message.format(
                msg_id = msg.id,
                ch_id  = msg.channel.id,
                server_id = msg.channel.guild.id,
                unit = unit
            )
        )
    
    def insert_unit_message(self, unit:str, msg_id:int, send_id:int):
        self.conn.execute(
            sql_format.insert_message_unit.format(
                unit = unit,
                msg_id = msg_id,
                send_id = send_id
            )
        )

    def master_webhook_by_unit(self, unit:str) -> str:
        c = self.conn.execute(sql_format.select_unit_from_master.format(unit))
        for row in c:
            return row[2]

    async def send(self, url:str, *, wait=False, **kwargs) -> discord.Message:
        async with aiohttp.ClientSession() as session:
            try:
                webhook = Webhook.from_url(url, adapter=AsyncWebhookAdapter(session))
            except discord.InvalidArgument:
                #webhook url is invalid
                await self.delete_by_webhook(url)
                return None
            try:
                msg = await webhook.send(wait = wait, **kwargs)
                return msg
            except discord.NotFound:
                await self.delete_by_webhook(url)
                return None

    async def help_cmd(self, msg:discord.Message) -> None:
        with open(config.help_fp, "r", encoding="utf-8") as f:
            text = f.read()
        await msg.channel.send(text)

    async def cmd(self, msg:discord.Message) -> bool:
        if not msg.author.guild_permissions.manage_guild:
            return False
        if msg.content.startswith(config.join_cmd):
            await self.join_unit(msg)
            return True
        elif msg.content.startswith(config.left_cmd):
            await self.left_unit(msg)
            return True
        elif msg.content.startswith(config.help_cmd):
            await self.help_cmd(msg)
            return True
        elif msg.content.startswith(config.list_cmd):
            await self.unit_list(msg)
            return True
        else:
            return False
    
    async def join_unit(self, msg:discord.Message):
        if await self.check_channel_connected(msg.channel.id):
            #channel is already connected
            await self.error_already_linkd(msg.channel)
            return None
        try:
            unit = msg.content.split(" ")[1]
        except:
            #unset unit name
            await self.error_unset_unit(msg.channel)
            return None
        if not self.check_char(unit):
            #unit name contains invalid characters
            await self.error_invalid_char(msg.channel)
            return None
        if not self.check_manage_webhook_permission(msg.channel):
            #bot don't have manage_webhook
            await self.error_manage_webhooks(msg.channel)
            return None
        if self.is_new_unit(unit):
            await self.new_unit(unit, msg)
        #join unit
        #create webhook
        webhook = await msg.channel.create_webhook(name=unit)
        url = webhook.url
        #insert unit DB
        self.conn.execute(
            sql_format.insert_unit.format(
                ch_id = msg.channel.id,
                unit  = unit,
                webhook = url
            )
        )
        #get unit servers
        self.conn.commit()
        c = self.conn.execute(sql_format.select_channel_by_unit.format(unit))
        get_server = lambda x: self.client.get_channel(x).guild.name
        servers = [get_server(r[0]) for r in c]
        content = self.create_join_content(msg.channel.guild, unit, servers)
        #send unit server
        c = self.conn.execute(sql_format.select_channel_by_unit.format(unit))
        for row in c:
            await self.send(row[2], **content)
        #send master server
        await self.send(self.master_webhook_by_unit(unit), **content)
        #end join_unit

    async def left_unit(self, msg:discord.Message):
        #select
        c = self.conn.execute(
            sql_format.select_from_unit_by_channel.format(msg.channel.id)
        )
        for row in c:
            #delete
            self.conn.execute(
                sql_format.delete_unit_by_channel.format(msg.channel.id)
            )
            break
        else:
            #not exist DB
            return None
        unit = row[1]
        left = self.client.get_channel(row[0]).guild
        url = row[2]
        #get unit servers
        c = self.conn.execute(sql_format.select_channel_by_unit.format(unit))
        get_server = lambda x: self.client.get_channel(x).guild.name
        servers = [get_server(r[0]) for r in c]
        content = self.create_left_content(left, unit, servers)
        #get and delete webhook
        async with aiohttp.ClientSession() as session:
            try:
                webhook = Webhook.from_url(url, adapter=AsyncWebhookAdapter(session))
                await webhook.send(**content)
                await webhook.delete()
            except Exception as e:
                print(e)
        #send unit server
        c = self.conn.execute(sql_format.select_channel_by_unit.format(unit))
        for row in c:
            await self.send(row[2], **content)
        #send master server
        await self.send(self.master_webhook_by_unit(unit), **content)     

    async def delete_by_webhook(self, url:str):
        #select
        c = self.conn.execute(
            sql_format.select_from_unit_by_webhook.format(url)
        )
        for row in c:
            #delete
            self.conn.execute(
                sql_format.delete_unit_by_webhook.format(url)
            )
            break
        else:
            #not exist DB
            return None
        unit = row[1]
        left = self.client.get_channel(row[0]).guild
        #get unit servers
        c = self.conn.execute(sql_format.select_channel_by_unit.format(unit))
        get_server = lambda x: self.client.get_channel(x).guild.name
        servers = [get_server(r[0]) for r in c]
        content = self.create_left_content(left, unit, servers)
        #send unit server
        c = self.conn.execute(sql_format.select_channel_by_unit.format(unit))
        for row in c:
            await self.send(row[2], **content)
        #send master server
        await self.send(self.master_webhook_by_unit(unit), **content)

    async def check_channel_connected(self, ch_id:int) -> bool:
        c = self.conn.execute(
            sql_format.select_unit_by_channel.format(ch_id)
        )
        for row in c:
            url = row[2]
            break
        else:
            #not exist unit DB
            return False
        #webhook url check
        channel = self.client.get_channel(ch_id)
        webhooks = await channel.webhooks()
        for webhook in webhooks:
            if webhook.url == url:
                return True
        return False

    def check_char(self, char:str) -> bool:
        try:
            match = re.match(r"^[a-zA-Z]+$", char)
            if match:
                return True #correct
        except Exception as e:
            print(e)
            return False
        return False

    def check_manage_webhook_permission(self, channel:discord.TextChannel) -> bool:
        return channel.permissions_for(channel.guild.me).manage_webhooks

    def is_new_unit(self, unit:str) -> bool:
        #access master table
        c = self.conn.execute(
            sql_format.select_unit_from_master.format(unit)
        )
        for row in c:
            return False
        return True

    async def new_unit(self, unit:str, msg:discord.Message):
        #create new channel
        overwrites = {self.mas_server.default_role: discord.PermissionOverwrite(send_messages=False)        }
        channel = await self.mas_server.create_text_channel(unit, overwrites=overwrites, category=self.mas_category)
        #create webhook
        webhook = await channel.create_webhook(name=unit)
        url = webhook.url
        #insert master DB
        self.conn.execute(
            sql_format.insert_master.format(
                unit = unit,
                channel = channel.id,
                webhook = url
            )
        )
        #create unit table
        self.conn.execute(sql_format.create_unit_table.format(unit))

    def is_mas_channel(self, msg:discord.Message) -> bool:
        return msg.channel.id == config.MAS_CHANNEL
    
    async def unit_list(self, msg:discord.Message):
        c = self.conn.execute(
            sql_format.select_unit_by_channel.format(msg.channel.id)
        )
        for row in c:
            unit = row[1]
            break
        else:
            #not exist DB
            return None
        c = self.conn.execute(
            sql_format.select_channel_by_unit.format(unit)
        )
        servers = list()
        for row in c:
            servers.append(self.client.get_channel(row[0]).guild.name)
        await msg.channel.send(self.create_group_list_content(unit, servers))

    async def master_cmd(self, msg:discord.Message):
        if msg.content.startswith(config.del_cmd):
            await self.delete_cmd(msg)
            return None
        elif msg.content.startswith(config.blacklist_cmd):
            await self.black_list_cmd(msg)
            return None
        elif msg.content.startswith(config.sql_cmd):
            await self.sql_cmd(msg)
            return None
        else:
            return None
    
    async def delete_cmd(self, msg:discord.Message):
        match = re.search(r"\d+", msg.content)
        if match is None:
            await self.error_unset_msg(msg.channel)
        target_id = match.group(0)
        target, unit = await self.search_msg(target_id)
        if target is None:
            #error
            await msg.channel.send(unit)
            return None
        messages = self.get_messages(target_id, unit)
        if messages is None:
            await self.error_no_exist_db(msg.channel)
            return None
        channels = [r[1].name for r in messages]
        check = await self.delete_cmd_check(msg, target, unit, channels)
        if not check:
            return None
        #delete action
        done = list()
        fail = list()
        for msg_id, ch in messages:
            check = await self.delete_message(ch.id, msg_id)
            done.append(ch.name) if check else fail.append(ch.name)
        #result
        text = bm.delete_cmd_result.format(unit=unit, msg_id=target_id)
        if done:
            text += bm.delete_cmd_result_done.format("\n\t".join(done))
        if fail:
            text += bm.delete_cmd_result_fail.format("\n\t".join(fail))
        await msg.channel.send(text)

    async def delete_cmd_check(self, msg:discord.Message, target:discord.Message, unit:str, channels:list) -> bool:
        reaction_message = await msg.channel.send(
            bm.delete_cmd_check.format(
                unit = unit,
                msg_id = target.id,
                author = str(target.author),
                channel = target.channel.name,
                server = target.channel.guild.name,
                channels = "\n\t".join(channels),
                content = target.content
            )
        )
        #add reaction
        await reaction_message.add_reaction("✅")
        await reaction_message.add_reaction("❌")

        def check(reaction:discord.Reaction, user:discord.User):
            if user == self.client.user:
                return False
            if reaction.message.id == reaction_message.id and reaction.emoji in ("✅", "❌"):
                return True
            return False

        try:
            reaction, user = await self.client.wait_for("reaction_add", check=check, timeout = 30)
        except asyncio.TimeoutError:
            await self.error_timeout(msg.channel)
            return None
        if reaction.emoji == "❌":
            await self.command_cancel(msg.channel)
            return False
        elif reaction.emoji == "✅":
            return True
        else:
            #unexpected error
            await self.error_unexpected(msg.channel, "delete_cmd_check, reaction.emoji")
            return False

    async def delete_message(self, ch_id:int, msg_id:int) -> bool:
        try:
            await self.client.http.delete_message(ch_id, msg_id)
            return True
        except:
            return False
    
    async def search_msg(self, msg_id:int) -> tuple:
        """
        return msg:discord.Message, unit:str
        """
        c = self.conn.execute(
            sql_format.select_message_by_msg_id.format(msg_id)
        )
        for row in c:
            msg_id, ch_id, server_id, unit = row
            break
        else:
            return None, error.no_exist_db
        try:
            channel = self.client.get_channel(ch_id)
            msg = await channel.fetch_message(msg_id)
            return msg, unit
        except Exception as e:
            return None, str(e)

    def get_messages(self, msg_id:int, unit:str) -> list:
        c = self.conn.execute(
            sql_format.select_send_message_from_group.format(
                msg_id = msg_id,
                unit = unit
            )
        )
        result = list()
        for row in c:
            ch = self.client.get_channel(row[1])
            if ch is None:
                continue
            result.append((row[0], ch))
        if len(result) > 0:
            return result
        return None

    def black_list(self, user:int) -> bool:
        c = self.conn.execute(sql_format.select_blacklist_by_user.format(user))
        for row in c:
            return True
        return False

    async def black_list_cmd(self, msg:discord.Message):
        try:
            action = msg.content.split()[1].strip().lower()
        except IndexError:
            await self.error_unset_action(msg.channel)
            return None
        if action == "show":
            await msg.channel.send(self.show_black_list())
            return None
        elif action == "add":
            #add
            await self.add_black_list(msg)
            return None
        elif action == "remove":
            #remove
            await self.remove_black_list(msg)
            return None
        else:
            #other action code
            await self.error_unknown_action(msg.channel)
            return None

    def show_black_list(self) -> str:
        c = self.conn.execute(sql_format.select_blacklist)
        text = "ブラックリストに登録されているユーザー一覧："
        for row in c:
            text += bm.blacklist_user.format(id=row[0], name=[1]) + "\n"
        return text

    async def add_black_list(self, msg:discord.Message):
        try:
            user_id = msg.content.split()[2].strip()
        except:
            await self.error_unset_action(msg.channel)
            return None
        #get user
        user = await self.client.fetch_user(int(user_id))
        if user is None:
            #not found
            await self.error_unknown_user(msg.channel)
            return None
        self.conn.execute(sql_format.insert_blacklist.format(user=user.id, name=str(user)))
        #result
        await msg.channel.send(bm.blacklist_add.format(id=user.id, name=str(user)))

    async def remove_black_list(self, msg:discord.Message):
        try:
            user_id = msg.content.split()[2].strip()
        except:
            await self.error_unset_action(msg.channel)
            return None
        #get user
        user = await self.client.fetch_user(int(user_id))
        if user is None:
            #not found
            await self.error_unknown_user(msg.channel)
            return None
        self.conn.execute(sql_format.delete_blacklist.format(user.id))
        #result
        await msg.channel.send(bm.blacklist_remove.format(id=user.id, name=str(user)))

    async def sql_cmd(self, msg:discord.Message):
        try:
            text = msg.content.split("\n")[1].strip()
        except:
            await self.error_unset_action(msg.channel)
            return None
        try:
            c = self.conn.execute(text)
            check = False
            result = "```\n"
            for row in c:
                result += str(row) + "\n"
                check = True
            result += "```"
            await msg.channel.send(result)
        except Exception as e:
            await msg.channel.send(str(e))
            return None

    async def command_cancel(self, channel:discord.TextChannel):
        await channel.send(bm.cancel)

    async def error_default(self, channel:discord.TextChannel, text:str):
        await channel.send(text)

    async def error_unexpected(self, channel:discord.TextChannel, text:str):
        await channel.send(error.unexpected.format(text))

    async def error_already_linkd(self, channel:discord.TextChannel):
        await channel.send(error.already_linkd)

    async def error_unset_unit(self, channel:discord.TextChannel):
        await channel.send(error.unset_unit)
    
    async def error_invalid_char(self, channel:discord.TextChannel):
        await channel.send(error.invalid_char)

    async def error_manage_webhooks(self, channel:discord.TextChannel):
        await channel.send(error.manage_webhooks)
    
    async def error_unset_msg(self, channel:discord.TextChannel):
        await channel.send(error.unset_msg)

    async def error_unknown_action(self, channel:discord.TextChannel):
        await channel.send(error.unknown_action)

    async def error_unknown_user(self, channel:discord.TextChannel):
        await channel.send(error.unknown_user)
    
    async def error_unset_action(self, channel:discord.TextChannel):
        await channel.send(error.unset_action)

    async def error_timeout(self, channel:discord.TextChannel):
        await channel.send(error.timeout)
    
    async def error_no_exist_db(self, channel:discord.TextChannel):
        await channel.send(error.no_exist_db)

link = Link(discord.Client())

@link.client.event
async def on_ready():
    print("start")
    await link.boot()

@link.client.event
async def on_message(message):
    #check bot
    if message.webhook_id is None and message.author.bot:
        return None
    #message channel is text Channel
    if not isinstance(message.channel, discord.TextChannel):
        return None
    if isinstance(message.author, discord.Member):
        #message is cmd?
        if link.is_mas_channel(message):
            await link.master_cmd(message)
            return None
        flag = await link.cmd(message)
        if flag:
            return None
    await link.main(message)
    
link.client.run(config.TOKEN)
