def history_parser(history_str: str) -> list:
    """Parse history string into a list of messages"""
    # TODO: Implement history parser : <USER></USER><br><BOT></BOT><br><USER></USER><br><BOT></BOT>
    # TODO: Return list of messages
    history_list = history_str.split("<br>")
    messages = []
    for message in history_list:
        message = message.strip()
        if message.startswith("<USER>"):
            message = message.replace("<USER>", "").replace("</USER>", "")
            user_message = {
                "role": "user",
                "content": message
            }
            messages.append(user_message)
        elif message.startswith("<BOT>"):
            message = message.replace("<BOT>", "").replace("</BOT>", "")
            bot_message = {
                "role": "assistant",
                "content": message
            }
            messages.append(bot_message)

    return messages