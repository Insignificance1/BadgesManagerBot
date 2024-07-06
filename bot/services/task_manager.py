import asyncio

from bot.settings.variables import bot

class TaskManager:
    def __init__(self):
        self.tasks = {}

    def create_loading_task(self, chat_id, name):
        task = asyncio.create_task(self.send_loading_message(chat_id), name=name)
        self.tasks[name] = task
        return task

    async def send_loading_message(self, chat_id):
        """
        Режим ожидания
        """
        message = await bot.send_message(chat_id, "Ожидайте, бот думает")
        dots = ""
        try:
            while True:
                if dots == "...":
                    dots = ""
                else:
                    dots += "."
                await bot.edit_message_text(f"Ожидайте, бот думает{dots}", chat_id=chat_id,
                                            message_id=message.message_id)
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            await bot.delete_message(chat_id=chat_id, message_id=message.message_id)

    def get_task_by_name(self, name):
        return self.tasks.get(name)

    async def cancel_task_by_name(self, name):
        task = self.get_task_by_name(name)
        if task:
            task.cancel()
            await task


task_manager = TaskManager()
