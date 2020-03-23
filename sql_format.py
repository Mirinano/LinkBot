#!python3.8
##insert
insert_message = "INSERT INTO message VALUES ({msg_id}, {ch_id}, {server_id}, '{unit}');"
insert_message_unit = "INSERT INTO {unit} VALUES ({msg_id}, {send_id});"
insert_unit = "INSERT INTO unit VALUES ({ch_id}, '{unit}', '{webhook}');"
insert_master = "INSERT INTO master VALUES ('{unit}', {channel},'{webhook}');"
insert_blacklist = "INSERT INTO black VALUES ({user}, '{name}');"
##create
create_unit_table = "CREATE TABLE IF NOT EXISTS {}(message INTEGER, send INTEGER);"

##select (search)
select_unit_by_channel = "SELECT * FROM unit WHERE channel={};"
choice_send_webhook = "SELECT * FROM unit WHERE unit='{unit}' AND channel!={channel};"
select_channel_by_unit = "SELECT * FROM unit WHERE unit='{}';"
select_from_unit_by_webhook = "SELECT * FROM unit WHERE webhook='{}';"
select_from_unit_by_channel = "SELECT * FROM unit WHERE channel={};"

select_unit_from_master = "SELECT * FROM master WHERE unit='{}';"

select_send_message_from_group = "SELECT send,channel FROM {unit} INNER JOIN message ON {unit}.send=message.message WHERE {unit}.message={msg_id};"
select_message_by_msg_id = "SELECT * FROM message WHERE message={};"

select_blacklist = "SELECT * FROM black;"
select_blacklist_by_user = "SELECT * FROM black WHERE user={};"

##delete
delete_unit_by_webhook = "DELETE FROM unit WHERE webhook='{}';"
delete_unit_by_channel = "DELETE FROM unit WHERE channel={};"
delete_blacklist = "DELETE FROM black WHERE user={};"
