from telethon import TelegramClient, events, errors
import time
import os
# import logging
# logging.basicConfig(
#     filename='app.log',
#     format='%(asctime)s %(levelname)s: %(message)s',
#     datefmt='%Y-%m-%d %H:%M:%S',
#     level=logging.ERROR
# )


def write_log(loop=None, context=None, exception=None):
    with open("log.txt", "w") as file:
        if loop:
            file.write(f'{time.asctime()}\n{loop}\n{context}\n\n')
        else:
            file.write(f'{time.asctime()}\n{exception}\n\n')


# https://superfastpython.com/asyncio-log-all-exceptions/
def never_retrieved_exceptions_handler(loop, context):  # обработчик "молчаливых" ошибок
    if str(context['exception']).startswith('No user has'):
        incorrect_linkname = str(context['exception']).split('"')[1]
        links.remove(incorrect_linkname)
        with open("links.txt", "w") as file:
            file.writelines(line + "\n" for line in links)
    else:
        write_log(loop=loop, context=context)
        #raise


def manual_authorization(PHONE_NUMBER, PASSWORD):
    if 'telethon_session.session' not in os.listdir(os.getcwd()):
        client = TelegramClient('telethon_session', API_ID, API_HASH, system_version="4.10.5 beta x64")

        def callback():
            with open('code.txt', 'w', encoding='utf-8') as code_file:
                code_file.write('Вместо звёздочек введите код авторизации: *****')
            while True:
                time.sleep(2)
                with open('code.txt', 'r', encoding='utf-8') as code_file:
                    code = code_file.read()[-5:]
                    if code.isdigit():
                        break
            return code

        client.start(phone=PHONE_NUMBER, password=PASSWORD, code_callback=callback)  # .connect() вызывает утечку памяти?
    else:
        client = TelegramClient('telethon_session', API_ID, API_HASH, system_version="4.10.5 beta x64")

    return client


try:
    with open('api_id, api_hash, phone, password.txt', 'r', encoding='utf-8') as user_data_file, \
            open('promo_messages.txt', 'r', encoding='utf-8') as promo_file, \
            open('links.txt', 'r', encoding='utf-8') as links_file, \
            open('keywords.txt', 'r', encoding='utf-8') as keywords_file:
        user_data_lines = user_data_file.readlines()
        API_ID = int(user_data_lines[0][33:-1])
        API_HASH = user_data_lines[1][35:-1]
        PHONE_NUMBER = user_data_lines[2][67:-1]
        PASSWORD = user_data_lines[3][75:]
        if PASSWORD[:4] == '****':
            PASSWORD = None
        links = list({line.strip().replace('https://t.me/', '')
                      for line in links_file.readlines() if line.strip()})
        keywords = list({line.strip().lower() for line in keywords_file.readlines() if line.strip()})
        promo_text = promo_file.read()
        client = manual_authorization(PHONE_NUMBER, PASSWORD)
except Exception as e:
    write_log(exception=e)


async def form_actual_links():
    global links
    actual_links = []
    for link in map(lambda link: link.replace('https://t.me/', ''), links):
        try:
            await client.get_entity(link)
            actual_links.append(link)
        except:
            continue
    links = actual_links
    with open("links.txt", "w") as file:
        file.writelines(line + "\n" for line in links)


try:
    with client:
        client.loop.run_until_complete(form_actual_links())
except Exception as e:
    write_log(exception=e)


while True:
    cache = set()  # декоратор детектил некоторые сообщения как новые несколько раз. Пришлось добавить кэш сообщений

    @client.on(events.NewMessage(chats=links))
    async def handler(event):
        message_obj = event.message
        mes_id = message_obj.id
        if mes_id in cache:
            return
        cache.add(mes_id)

        # проверяем если сообщение найдено в папке Избранное
        if hasattr(message_obj.peer_id, 'user_id'):
            channel_id = message_obj.peer_id.user_id
            mess_text = message_obj.text
            global links
            global keywords

            # добавляем ссылки
            if mess_text.startswith('+lnk'):
                new_links = map(lambda link: link.replace('https://t.me/', ''), mess_text.split()[1:])
                actual_new_links = []
                for link in new_links:
                    if link in links:
                        continue
                    try:
                        await client.get_entity(link)
                        actual_new_links.append(link)
                    except:
                        continue
                links.extend(actual_new_links)
                with open("links.txt", "w") as file:
                    file.writelines(line + "\n" for line in links)
                await client.send_message(
                    channel_id,
                    f'!Сервисное сообщение:\nadded {len(actual_new_links)} new actual link(s)',
                    reply_to=mes_id
                )
                client.disconnect()

            # удаляем ссылки
            elif mess_text.startswith('-lnk'):
                links_to_del = [link.replace('https://t.me/', '') for link in mess_text.split()[1:]]
                links = [link for link in links if link not in links_to_del]
                with open("links.txt", "w") as file:
                    file.writelines(line + "\n" for line in links)
                await client.send_message(
                    channel_id,
                    f'!Сервисное сообщение:\ndeleted {len(links_to_del)} link(s)',
                    reply_to=mes_id
                )
                client.disconnect()

            # добавляем ключевые слова
            elif mess_text.startswith('+kw'):
                new_keywords = [kw.lower() for kw in mess_text[4:].split('*') if kw.lower() not in keywords]
                keywords.extend(new_keywords)
                keywords = list(set(keywords))
                with open("keywords.txt", "w", encoding='utf-8') as file:
                    file.writelines(line + "\n" for line in keywords)
                await client.send_message(
                    channel_id,
                    f'!Сервисное сообщение:\nadded {len(new_keywords)} new keyword(s)',
                    reply_to=mes_id
                )
                client.disconnect()
            # удаляем ключевые слова
            elif mess_text.startswith('-kw'):
                keywords_to_del = [kw.lower() for kw in mess_text[4:].split('*')]
                keywords = [kw for kw in keywords if kw not in keywords_to_del]
                with open("keywords.txt", "w", encoding='utf-8') as file:
                    file.writelines(line + "\n" for line in keywords)
                await client.send_message(
                    channel_id,
                    f'!Сервисное сообщение:\ndeleted {len(keywords_to_del)} keyword(s)',
                    reply_to=mes_id
                )
                client.disconnect()
            # добавляем/изменяем текст промо-сообщения
            elif mess_text.startswith('promo'):
                global promo_texts
                promo_text = mess_text[6:]
                with open('promo_messages.txt', 'w', encoding='utf-8') as file:
                    file.write(promo_text)
                await client.send_message(
                    channel_id,
                    f'!Сервисное сообщение:\nтекст промо-сообщения успешно изменён',
                    reply_to=mes_id
                )
                client.disconnect()
            # получаем информацию о текущих ключевых словах /фразах, тексте промо-сообщения, отслеживаемых ресурсах
            elif mess_text == 'info':
                try:
                    service_message = (f'!Сервисное сообщение:\nТекущие ключевые '
                                       f'слова/фразы:\n{"    \n".join(sorted(keywords))}\n\n'
                                       f'Промо-сообщение:\n{promo_text}\n\n'
                                       f'Текущие ресурсы на мониторинге '
                                       f'(me не удалять):\n{"    \n".join(sorted(links))}')
                    await client.send_message(channel_id, service_message, reply_to=mes_id)
                except:
                    files = ['links.txt', 'keywords.txt', 'promo_messages.txt']
                    uploaded_files = []
                    for file_path in files:
                        with open(file_path, 'rb') as f:
                            uploaded_file = await client.upload_file(f)
                            uploaded_files.append(uploaded_file)
                    await client.send_file(channel_id, file=uploaded_files, caption='!Сервисное сообщение:\nВ файле '
                                                                                    'со ссылками всегда должна '
                                                                                    'быть ссылка me - '
                                                                                    'не удаляйте её')
                client.disconnect()
        else:
            channel_id = message_obj.peer_id.channel_id
            for keyword in keywords:
                if keyword in message_obj.text:
                    if message_obj.out:
                        break
                    time.sleep(3)
                    try:
                        await client.send_message(channel_id, promo_text, reply_to=mes_id)
                    except:
                        pass
                    client.disconnect()
                    break


    try:
        with client:
            # configure the event loop to call a custom function for each exception raised in an asyncio program
            client.loop.set_exception_handler(never_retrieved_exceptions_handler)
            # Запускаем клиента и ждем событий
            client.run_until_disconnected()
    except Exception as e:
        write_log(exception=e)
