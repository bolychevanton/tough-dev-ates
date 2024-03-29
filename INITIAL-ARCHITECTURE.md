# Вступление

Настоящий документ описывает архитектуру учебного проекта aTES для курса Асинхронная Архитектура и сделан в рамках нулевого домашнего задания. 

- [Вступление](#вступление)
- [Верхнеуровневое описание архитектуры](#верхнеуровневое-описание-архитектуры)
  - [Общий поток данных](#общий-поток-данных)
  - [Ключевые сервисы и их роли](#ключевые-сервисы-и-их-роли)
  - [Рабочий процесс](#рабочий-процесс)
- [Детальное описание архитектуры](#детальное-описание-архитектуры)
  - [Message Broker](#message-broker)
  - [Web Server](#web-server)
  - [Database](#database)
    - [users](#users)
    - [tasks](#tasks)
    - [logs](#logs)
    - [task_prices](#task_prices)
    - [account_transfers](#account_transfers)
  - [Auth Service](#auth-service)
    - [Rest API](#auth-service-rest-api)
  - [Task-Tracker Service](#task-tracker-service)
    - [REST API](#task-tracker-service-rest-api)
  - [Accounting Service](#accounting-service)
    - [Обработка сообщений](#обработка-сообщений)
    - [REST API](#accounting-service-rest-api)
  - [Service Analytics](#service-analytics)
    - [REST API](#service-analytics-rest-api)
  - [Payment Service](#payment-service)
- [Комментарии](#комментарии)
  - [Мотивировка выбора архитектуры](#мотивировка-выбора-архитектуры)   
  - [Как решать проблемы с данными](#как-решать-проблемы-с-данными)
  - [Проблемные места в архитектуре](#проблемные-места-в-архитектуре)
 
# Верхнеуровневое описание архитектуры
## Общий поток данных

- [Web Server](#web-server) - это точка входа для пользователей, через которую они могут взаимодействовать с системой aTES для регистрации, авторизации и работы с задачами и отчетами. Веб-сервер взаимодействует с другими сервисами через REST API для выполнения запросов пользователей.

- [Message Broker](#message-broker) обеспечивает асинхронный обмен сообщениями между сервисами

- [Database](#database) - центральное хранилище данных, содержащее информацию о пользователях, задачах, финансовых операциях и другую необходимую информацию.
## Ключевые сервисы и их роли

- [Auth Service](#auth-service) отвечает за регистрацию и аутентификацию пользователей, выдачу токенов и хранение данных о пользователях в соответствующей таблице базы данных.

- [Task-Tracker Service](#task-tracker-service) управляет процессами создания, назначения и отслеживания выполнения задач. Служба регистрирует журналы активности, а также информирует [Accounting Service](#accounting-service) о финансовых изменениях, связанных с заданиями через [Message Broker](#message-broker).

- [Accounting Service](#accounting-service) управляет финансовыми операциями, включая начисления и списания средств, а также формирует отчетность по остаткам и операциям. 

- [Service Analytics](#service-analytics) анализирует финансовые и операционные показатели, предоставляя административные отчеты и информацию о работе компании.

- [Payment Service](#payment-service) автоматизирует процесс оплаты, регулярно инициируя расчеты с сотрудниками через [Accounting Service](#accounting-service). 

## Рабочий процесс

Пользователи взаимодействуют с системой через веб-интерфейс, который обслуживается [Web Server](#web-server).  При регистрации или аутентификации запросы отправляются в службу [Auth Service](#auth-service), которая возвращает соответствующий токен для доступа к системе.

При работе с заданиями служба  [Task-Tracker Service](#task-tracker-service)  регистрирует и назначает задания, а также отслеживает их выполнение. Вся информация о задачах хранится в [Database](#database). Там же хранятся и все логи о действиях пользователей, а также все финансовые операции со счетом. Важные события, такие как создание, назначение и завершение задач, передаются в [Accounting Service](#accounting-service) для ведения финансового учета.



# Детальное описание архитектуры

В данном разделе более подробно описана работа всех сущностей внутри настоящего проекта. 

## Message Broker

обеспечивает асинхронный обмен сообщениями между сервисами

## Web Server

это точка входа для пользователей, через которую они могут взаимодействовать с системой aTES для регистрации, авторизации и работы с задачами и отчетами. Веб-сервер взаимодействует с другими сервисами через REST API для выполнения запросов пользователей, а именно
- [Auth Service REST API](#auth-service-rest-api)
- [Task-Tracker Service REST API](#task-tracker-service-rest-api)
- [Accounting Service REST API](#accounting-service-rest-api)
- [Service Analytics REST API](#service-analytics-rest-api)

## Database
центральное хранилище данных, содержащее информацию о пользователях, задачах, финансовых операциях и другую необходимую информацию.

Ниже перечислены все необходимые таблицы с описанием столбцов.
### users
Tаблица, содержащая информацию про пользователей

- `id: int, primarykey` 
- `role: Enum[administrator|manager|developer|boss|accountant|internalservice|other]`
- `login: str`
- `email: str`
- `salt: int`
- `hash: str`
### tasks
Таблица содержащая информацию про задачи
- `id: int, primarykey`
- `name: str`
- `description: str`
- `assigned_to: int, foreignkey(users.id)`
- `is_finished: bool`
- `created_at: timestamp`
### logs
Таблица, содержащая логи по действиям с задачами
- `id: int, primarykey`
- `task_id: int, foreignkey(tasks.id)`
- `timestamp: timestamp`
- `type: Enum[create|assign|complete|other]`
- `description: Optional[str]`
### task_prices
Таблица, содержащая информацию по ценам на задачи
- `task_id: int, primarykey, foreignkey(tasks.id)`
- `assign_price: float`
- `complete_price: float`

### account_transfers
Таблица, содержащая информацию о начислениях и списаниях
- `id: int, primarykey`
- `timestamp: timestamp`
- `delta_balance: float`
- `description: str`

## Auth Service

твечает за регистрацию и аутентификацию пользователей, выдачу токенов и хранение данных о пользователях в соответствующей таблице базы данных.
### Auth Service REST API

- `register_user` — создаёт юзера с конкретной ролью
    - Делает запись в бд о новом юзере в таблицу [users](#users)
- `auth_user` — через логин-пароль возвращает токен
        - Читает таблицу [users](#users)

## Task-Tracker Service

Управляет задачами, их созданием, назначением и отслеживанием их выполнения.  Служба регистрирует журналы активности, а также информирует [Accounting Service](#accounting-service) о финансовых изменениях, связанных с заданиями через [Message Broker](#message-broker).
### Task-Tracker Service REST API

- `create_task` — создается новая задача.
  - Пишет в [tasks](#tasks) запись о новой задаче. Попуг ассайнится случайно автоматически.
  - Пишет в [logs](#logs) информацию о том, что задача была создана
  - посылает асинхронное сообщение в [Service Accounting](#service-accounting) о новой задаче
- `reassign_tasks` — реассайнит случайным образом попугов на все незаконченные таски (доступна только администраторам и менеджерам)
  - делает соответствующие записи в бд в таблицу [tasks](#tasks), модифицируя поле `assigned_to`
  - Пишет в [logs](#logs) информацию о том, что задачи были за реассайнены
  - посылает асинхронные сообщения в в [Service Accounting](#service-accounting) о всех заассайненных задачах
- `complete_task`: отметь задачу как выполненную
  - Меняет статус задачи в [tasks](#tasks)
  - Пишет в [logs](#logs) информацию о том, что задача была выполнена
  - посылает асинхронное сообщение в [Service Accounting](#service-accounting) о том, что задача выполнена
- `show_my_assigned_tasks` — показывает для залогиненного юзера список его задач
  - читает все соответсвующие данные из [tasks](#tasks)
- `show_all_assigned_tasks` — показывает админам и менеджерам все задачи и кому они заассайнены
  - читает данные из [tasks](#tasks)

## Accounting Service

Отвечает за учет финансовых операций, начисление и списание средств с аккаунтов сотрудников, а также за предоставление административных отчетов и информации для сотрудников. 
## Обработка сообщений
- При получении сообщения о том, что задача создана 
  - пишет в [task_prices](#task_prices) её цены
  - создает запись в [account_transfers](#account_transfers) о списании 
- При получении сообщения о том, что задача заасайнена
  - создает запись в [account_transfers](#account_transfers) о списании
- При получении сообщения о том, что задача была выполнена
  - создает запись в [account_transfers](#account_transfers) о начислении
### Accounting Service REST API

- `show_balance` - показывает текущий баланс сотрудника
  - Делает sqlзапрос в [account_transfers](#account_transfers)
- `show_account_transfers` показывает лог операций (за определенный период) для сотрудника 
  - делает sql запрос в [account_transfers](#account_transfers)
- `pay_to_workers` - рассчитывается с сотрутниками за день
  - логгирует соответствующие записи в [account_transfers](#account_transfers)
  - отправляет уведомление на почту 
- `show_all_account_transfers` - показывает лог операций (за определенный период) для компании. Только для бухгалтеров
## Service Analytics

Собирает и обрабатывает данные о финансовых показателях и производительности компании, предоставляя администраторам аналитические отчеты.

### Service Analytics REST API
- `today_income` - показывает доход за сегодня
  - читает данные из [account_transfers](#account_transfers)
- `negative_balances`
  - читает данные из [account_transfers](#account_transfers)
- `show_the_most_expensive_task` - показывает самую дорогую задачу
  - читает данные из [task_prices](#task_prices)

## Payment Service

- Каждые 24 часа дергает ручку [Accounting Service REST API](#accounting-service-rest-api)/`pay_to_workers`

# Комментарии 

## Мотивировка выбора архитектуры

- Архитектура проектировалась по приниципу: я четко понимаю как имплементировать и запустить каждый компонент архитектуры. Если я не мог прийти к однозначному решению, то оставлял этот момент. По этой причине постарался описать все волнующие меня недоработки в разделах
  - [Как решать проблемы с данными](#как-решать-проблемы-с-данными)
  - [Проблемные места в архитектуре](#проблемные-места-в-архитектуре) 

- В лекции было сказано, что сервисы стоит проектировать, мотивируясь бизнес-логикой. Так как техническое задание явно декларирует, из каких бизнес-компонент должен состоять проект, то сервисы
  - [Auth Service](#auth-service) (он не был явно продекларирован, как отдельный раздел в тз, но явно фигурировал везде как "сервис авторизации")
  - [Task-Tracker Service](#task-tracker-service)
  - [Accounting Service](#accounting-service)
  - [Service Analytics](#service-analytics)
  
  появились практически сразу. Мной было принято решение сильно не плодить дополнительные сущности, так как при попытке ввести новые сущности я сильно погружался в детали и понимал, что не смогу прийти к конечной версии этого домашнего задания за приемлемое время.

- [Payment Service](#payment-service) был выделен в отдельный сервис, так как мне показалось, что отдельный воркер, который выполняет одни и те же действия через равные промежутки времени, очень естественно выделить в отдельный микросервис

- Сервисы
  - [Auth Service](#auth-service)
  - [Task-Tracker Service](#task-tracker-service)
  - [Accounting Service](#accounting-service)
  
  используют REST API для коммуникации с веб-сервером, так как явно реализуют парадигму Frontend-Backend, где Frontend - это сам веб-сервер, а бекенд из себя представляет набор сервисов.

## Как решать проблемы с данными

- В мессадж брокере надо хранить все события на харде на случай, если упадет [Accounting Service](#accounting-service)
- Если упадет база данных, то надо иметь точную реплику. Как вариант, всегда писать сразу в 2 базы данных. Перед каждой записью и чтением проверять, что данные консистентны, а также проверять, что данные консистенты и после записи. Если нет, останавливать проект до обнаружения всех проблем. Можно  на этот случай завести отдельный сервис, который останавливает работу проекта и уведомляет через [Web Server](#web-server).
- Любые инсерты в бд надо делать в рамках одной сессии
- Если упадет сеть, но все контейнеры будут на одной тачке, то тогда проблема решается через ручным `sudo docker compose restart`, когда проблема с сетью будет восстановлена.
- Если будет использоваться кластер, то надо сделать реплики для всех сущностей. В частности, отдельно сконфигурировать [Message Broker](#message-broker) для отказоустойчивой работы в рамках кластера.

## Проблемные места в архитектуре

- Требуется завести отдельный сервис для экстренной остановки проекта, если возникает какая-нибудь проблема.  
- Если способ хранения пользователей в таблице [users](#users) не самый лучший и требуется подобрать лучший способ хранения. Вообще, отдельно подумать насчёт Data Security. Но я, к сожалению, не специалист.
- Если упадет [Accounting Service](#accounting-service) уже после создания тасков в [Task-Tracker Service](#task-tracker-service), то решить эту проблему руками будет сложно. Возможно, требуется перед деплоем сделать health-check, что определенный набор сценариев работает верно. Нужно создать определенные механизмы валидации, что все заранее спланированные сценарии отрабатывают верно. Как вариант, заставлять все сервисы логировать в [Message Broker](#message-broker) и дальше завести отдельный сервис, который валидирует, что все сервисы посылают сообщения согласно спланированным сценариям и кричать о проблеме, откатывая изменения при необходимости. Другим решением этой проблемы может быть введение отдельного сервиса DBInserter, который будет по построению делать все инсерты, требующие согласованности, в рамках одной сессии.  
