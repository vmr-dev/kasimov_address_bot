<h2 align="center"> Инструкция по развёртыванию бота </h2>

### 0. Создание бота в телеграм:

Перед развёрткой нужно создать телеграм бота в BotFather,
далее нужно скопировать его API_TOKEN для дальнейшей работы.

### 1. Создание сервисных аккаунтов

Для работы большинства функций необходимо настроить
сервисные аккаунты и назначить им определённые роли.

- **queue-manager**: сервисный аккаунт для отправки сообщений
  
  - **Роли**:
    
    - `serverless.functions.invoker`
    - `editor`
  
  - **Ключи**: 
    
    - **статический ключ** для работы с очередями
      (токен+секретный токен) их нужно сразу же 
      сохранить, потому что секретный ключ сразу скрывается

- **ydb-manager**: сервисный аккаунт для доступа к БД
  
  - **Роли**:
    - `ydb-editor`
    - `ydb-viewer`

### 2. Создание базы данных

Для хранения и работы бота также нужна БД яндекса,
это будет serverless YDB. После её создания нужно
также создать следующие таблицы.

**Название базы**: `kasimov-houses-db`

**Лучше также сразу же сохранить** `Эндпоинт` и `Размещение базы данных`

- `houses`: хранение информации об адресах домов
  
  | Имя             | Тип    | Первичный ключ |
  |:---------------:|:------:|:--------------:|
  | address         | `utf8` | Да             |
  | additional_info | `Json` | Нет            |
  | company_name    | `utf8` | Нет            |

- `companies`: хранение информации о компаниях
  
  | Имя             | Тип    | Первичный ключ |
  |:---------------:|:------:|:--------------:|
  | name            | `utf8` | Да             |
  | additional_info | `Json` | Нет            |

- `users`: хранение информации о пользователях

  | Имя                 |         Тип         |   Первичный ключ    |
  |:-------------------:|:-------------------:|:-------------------:|
  | chat_id             |       `utf8`        |         Да          |
  | date                |       `utf8`        |         Нет         |
  | paid_requests_count |      `Uint32`       |         Нет         |
### 3. Создание очереди сообщений

Для того чтобы функция приёма заданий и их обработки
могли сообщаться, должна быть создана очередь сообщений.
***Сразу же сохраняем её URL для доступа из функций***

- **Название очереди**: `kasimov-houses-tasks`
- **Тип Очереди**: `Стандартная` 
- **Таймаут видимости**: `10 минут` (на случай если задача выполняется долго, 
  и мы ещё не получили от функции статус выполнения, так мы избегаем дублирования задач)

### 4. Создание функции приёма сообщений

Эта функция вебхук, которую будет дёргать наш телеграм бот
при поступлении новых сообщений от пользователей.
Она отправляет в очередь задания для следующей функции (обработчика).

1. **Создать функцию**: 'kasimov-houses-telegram-webhook'
2. **Переместить** файлы скриптов и requirements.txt из директории
   bot-webhook в редактор функции
3. **Создать переменные окружения для функции**:
   - `AWS_ACCESS_KEY_ID`: токен статического ключа из
     сервисного аккаунта queue-manager
   - `AWS_SECRET_ACCESS_KEY`: секрет статического ключа
     из сервисного аккаунта queue-manager
   - `QUEUE_ENDPOINT`: Ссылка-эндпоинт нашей очереди
4. **Назначить сервисный аккаунт**: `queue-manager`
5. **Назначить таймаут**: `60 секунд`
6. **Сделать функцию публичной**

### 5. Создание функции обработки сообщений

Эта функция служит обработчиком заданий от пользователя
она же отвечает на запросы пользователя в отдельных хендлерах.

1. **Создать функцию**: `kasimov-houses-tasks-processor`
2. **Переместить** файлы скриптов и requirements.txt из директории
   bot-message-processor в редактор функции
3. **Создать переменные окружения для функции**:
   - `BOT_TOKEN`: токен телеграм бота для ответов
   - `YDB_ENDPOINT`: Эндпоинт из YDB
   - `YDB_PATH`: Размещение базы данных из YDB
   - `DADATA_API_KEY`: Ключ апи для подсказок от dadata.ru
   - `DADATA_SECRET_KEY`: Секрет для подсказок от dadata.ru
4. **Назначить сервисный аккаунт**: `ydb-manager`
5. **Назначить таймаут**: `600 секунд` 

### 6. Создание триггера для поступающих в очередь сообщений

Для того чтобы задачи могли перемещаться от вебхука к
обработчику создаём триггер:

- **Имя триггера**: `kasimov-houses-assign-task`
- **Тип триггера**: `Message Queue`
- **Запускаемый ресурс**: `Функция`
- **Очередь сообщений**: `kasimov-houses-tasks`
- **Сервисный аккунт для очереди**: `queue-manager`
- **Функция**: `kasimov-houses-tasks-processor`
- **Сервисный аккаунт функции**: `queue-manager`

### 7. Последний этап - установка вебхука для нашего бота

В директории tools есть скрипт для установки вебхука 
нашему боту.

1. Переменная WEBHOOK_URL = вебхук фукнции `kasimov-houses-telegram-webhook`
2. Переменная BOT_TOKEN = токен нашего бота
3. Запустить скрипт
4. Подождать около 5 секунд
5. Вырубить скрипт вручную, так как функция установки
   вебхука блокирующая, и не даст ему завершиться.
   (В дальнейшем можно делать простой реквест)
