from telethon import TelegramClient, events
import time
import os
from random import randint, choice
import tkinter as tk
import os
import asyncio


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


def manual_authorization(PHONE_NUMBER, PASSWORD):
    if 'telethon_session.session' not in os.listdir(os.getcwd()):
        print(1)
        client = TelegramClient('telethon_session', API_ID, API_HASH, system_version="4.10.5 beta x64")
        print(2)

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


# get user data from files and create Client
try:
    with open('api_id, api_hash, phone, password.txt', 'r', encoding='utf-8') as user_data_file, \
            open('promo_messages.txt', 'r', encoding='utf-8') as promo_file, \
            open('links.txt', 'r', encoding='utf-8') as links_file, \
            open('keywords.txt', 'r', encoding='utf-8') as keywords_file, \
            open('reply_range.txt', 'r', encoding='utf-8') as reply_range_file, \
            open('spec_channel_link.txt', 'r', encoding='utf-8') as spec_channel_file:
        user_data_lines = user_data_file.readlines()
        API_ID = int(user_data_lines[0][33:-1])
        API_HASH = user_data_lines[1][35:-1]
        PHONE_NUMBER = user_data_lines[2][67:-1]
        PASSWORD = user_data_lines[3][75:]
        spec_channel_link = spec_channel_file.read()
        if PASSWORD[:4] == '****':
            PASSWORD = None
        links = list({line.strip().replace('https://t.me/', '')
                      for line in links_file.readlines() if line.strip()})
        keywords = list({line.strip().lower() for line in keywords_file.readlines() if line.strip()})
        promo_texts = promo_file.read().split('\n---------------------------------\n')
        reply_range_start, reply_range_end = map(int, reply_range_file.read().split())
        if reply_range_start > 60:
            reply_range_start = 59
        if reply_range_end > 60:
            reply_range_end = 60
        client = manual_authorization(PHONE_NUMBER, PASSWORD)
        usernames_to_stories = set()
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


async def form_and_send_storymess():
    """
    generates and sends posts/s with a picture and marked users to a special chat/channel
    for further work (transformation into a story)
    """
    global usernames_to_stories
    while len(usernames_to_stories) >= 5:
        five_usernames = [usernames_to_stories.pop() for _ in range(5)]
        caption = ' '.join(
            map(lambda username: username if username[0] == '@' else '@' + username, five_usernames))
        for el in os.listdir(os.getcwd()):
            if el.startswith('pic_to_story'):
                await client.send_message(spec_channel_link, message=caption, file=el)
                #client.disconnect()
                break


def start_monitoring():
    result_label.config(text='Мониторинг...')
    root.update()
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
                global reply_range_start
                global reply_range_end
                global usernames_to_stories

                # добавляем ссылки
                if mess_text.startswith('+lnk '):
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
                elif mess_text.startswith('-lnk '):
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
                elif mess_text.startswith('+kw '):
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
                elif mess_text.startswith('-kw '):
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
                # добавляем текст промо-сообщения
                elif mess_text.startswith('+promo '):
                    global promo_texts
                    new_promo_text = mess_text[7:]
                    promo_texts.append(new_promo_text)
                    with open('promo_messages.txt', 'a+', encoding='utf-8') as file:
                        file.write('\n---------------------------------\n' + new_promo_text)
                    await client.send_message(
                        channel_id,
                        f'!Сервисное сообщение:\nтекст промо-сообщения добавлен',
                        reply_to=mes_id
                    )
                    client.disconnect()
                # удаляем текст промо-сообщения
                elif mess_text.startswith('-promo '):
                    #global promo_texts
                    promo_text_to_del = mess_text[7:]
                    promo_texts.remove(promo_text_to_del)
                    with open('promo_messages.txt', 'w', encoding='utf-8') as file:
                        file.write('\n---------------------------------\n'.join(promo_texts))
                    await client.send_message(
                        channel_id,
                        f'!Сервисное сообщение:\nтекст промо-сообщения удалён',
                        reply_to=mes_id
                    )
                    client.disconnect()
                # получаем информацию о текущих ключевых словах /фразах, тексте промо-сообщения,
                # отслеживаемых ресурсах, времени ответа
                elif mess_text == 'info':
                    try:
                        service_message = (f'!Сервисное сообщение:\nТекущие ключевые '
                                           f'слова/фразы:\n{"    \n".join(sorted(keywords))}\n\n'
                                           f'Промо-сообщение\я:'
                                           f'\n{"\n---------------------------------\n".join(promo_texts)}\n\n'
                                           f'Текущие ресурсы на мониторинге '
                                           f'(me не удалять):\n{"    \n".join(sorted(links))}\n\n'
                                           f'Диапазон времени ответа:\n{reply_range_start}-{reply_range_end} секунд '
                                           f'включительно\n\nСсылка на канал для стори-заготовок: {spec_channel_link}')
                        await client.send_message(channel_id, service_message, reply_to=mes_id)
                    except:
                        files = ['links.txt', 'keywords.txt', 'promo_messages.txt', 'reply_range.txt', 'spec_channel_link.txt']
                        uploaded_files = []
                        for file_path in files:
                            with open(file_path, 'rb') as f:
                                uploaded_file = await client.upload_file(f)
                                uploaded_files.append(uploaded_file)
                        await client.send_file(channel_id, file=uploaded_files,
                                               caption='!Сервисное сообщение:\nВ файле '
                                                       'со ссылками всегда должна '
                                                       'быть ссылка me - '
                                                       'не удаляйте её')
                    client.disconnect()
                # устанавливаем диапазон времени ответа
                elif mess_text.startswith('rt '):
                    reply_range_start, reply_range_end = map(int, mess_text.split()[1:])
                    if reply_range_start > 60:
                        reply_range_start = 59
                    if reply_range_end > 60:
                        reply_range_end = 60
                    with open("reply_range.txt", "w", encoding='utf-8') as file:
                        file.writelines(line + " " for line in (str(reply_range_start), str(reply_range_end)))
                    await client.send_message(
                        channel_id,
                        f'!Сервисное сообщение:\nустановлен диапазон {reply_range_start}-{reply_range_end} '
                        f'секунд включительно',
                        reply_to=mes_id
                    )
                    client.disconnect()
                # добавляем вручную юзернеймы для отметки в сторисах
                elif mess_text.startswith('+users'):
                    usernames = mess_text.split()[1:]
                    [usernames_to_stories.add(username) for username in usernames]
                    await client.send_message(
                        channel_id,
                        f'!Сервисное сообщение:\nдобавлены к отметке в стори {len(usernames)} юзеров',
                        reply_to=mes_id
                    )
                    if len(usernames_to_stories) >= 5:
                        await form_and_send_storymess()
                    client.disconnect()
                elif mess_text.startswith('spec channel'):
                    link = mess_text.split()[2]
                    await client.send_message(
                        channel_id,
                        f'!Сервисное сообщение:\nссылка на текущий канал для заготовок изменена',
                        reply_to=mes_id
                    )
                    client.disconnect()
            else:
                for keyword in keywords:
                    if keyword in message_obj.text.lower():
                        # если сообщение в мониторящемся чате исходящее, значит не отвечаем [самому себе]
                        if message_obj.out:
                            break
                        channel_id = message_obj.peer_id.channel_id

                        # add username to the story marks
                        try:
                            sender = await event.get_sender()
                            sender_username = sender.username
                            if sender_username:
                                usernames_to_stories.add(sender_username)
                                if len(usernames_to_stories) >= 5:
                                    await form_and_send_storymess()
                        except:
                            pass

                        # send the promo message (reply)
                        await asyncio.sleep(randint(reply_range_start, reply_range_end))
                        try:
                            await client.send_message(channel_id, choice(promo_texts), reply_to=mes_id)
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


# start_monitoring()


# Создаем главное окно приложения
root = tk.Tk()
root.title("monitoring Telegram chats and form posts for the stories")
root.geometry("900x100")
# Кнопка для старта парсинга
start_button = tk.Button(root, text="Начать мониторинг", command=start_monitoring, fg='green')
start_button.pack(pady=10)
# Создаем метку для вывода результата
result_label = tk.Label(root, text='После запуска программа может быть в статусе "Не отвечает". Это '
                                   'нормально - не обращайте внимания', font=("Helvetica", 12))
result_label.config(wraplength=800)
result_label.pack(pady=10)
# Запускаем основной цикл приложения
root.mainloop()
