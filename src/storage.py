class StorageManager:
    def __init__(self, page):
        self.page = page

    def get(self, key, default=None):
        """Получение значения по ключу с возможностью указания значения по умолчанию."""
        if self.page.client_storage.contains_key(key):
            return self.page.client_storage.get(key)
        return default

    def set(self, key, value):
        """Установка значения по ключу."""
        self.page.client_storage.set(key, value)

    def contains_key(self, key):
        """Проверка наличия ключа."""
        return self.page.client_storage.contains_key(key)

    def remove(self, key):
        """Удаление ключа."""
        self.page.client_storage.remove(key)

    def get_keys(self, prefix=""):
        """Получение списка ключей."""
        return self.page.client_storage.get_keys(prefix)