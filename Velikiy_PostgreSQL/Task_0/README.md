# 🔧 Задание 0 (Установка и настройка PostgreSQL 16 с использованием Ansible)

Tasks:

    0.0. Воткнуть дополнительный диск в вашу виртуалку (но можно просто выделить партицию на текущем диске) в качестве отдельного диска под данные базы;
    0.1. установить postgresql.

*Руками проинициализировать инстанс БД с данными в папке /pg_data/16/*

---
# Установка и настройка PostgreSQL 16 с использованием Ansible (документация)

## 📋 Содержание

1. [Введение](#1-введение)
2. [Подготовка инфраструктуры](#2-подготовка-инфраструктуры)
3. [Настройка дисков](#3-настройка-дисков)
4. [Подготовка проекта Ansible](#4-подготовка-проекта-ansible)
5. [Настройка Ansible Vault](#5-настройка-ansible-vault)
6. [Конфигурационные файлы](#6-конфигурационные-файлы)
7. [Playbook для установки PostgreSQL](#7-playbook-для-установки-postgresql)
8. [Запуск и проверка](#8-запуск-и-проверка)
9. [Устранение неполадок](#9-устранение-неполадок)
10. [Контрольный чек-лист](#10-контрольный-чек-лист)

---

## 1. Введение

В данном руководстве описана полная установка PostgreSQL 16 на два сервера с использованием Ansible. Особое внимание уделено:

- Использованию отдельного диска для данных БД (`/pg_data`)
- Безопасному хранению паролей через Ansible Vault
- Автоматизации всех этапов настройки

### Требования

| Компонент | Требование |
|-----------|------------|
| ОС | Debian 13 |
| Количество серверов | 2 |
| Ansible | Установлен на управляющей машине |
| SSH | Доступ к серверам по ключу |
| Диск | Дополнительный диск для данных БД |

![alt text](photos/image-6.png)
---

## 2. Подготовка инфраструктуры

### 2.1. Server1 - Установка с нуля

При установке Debian на первый сервер добавьте второй диск для данных PostgreSQL.

**Шаг 1:** На этапе разбиения дисков выберите ручное разбиение (Manual partitioning)

**Шаг 2:** Настройте первый диск (`/dev/vda`) для системы:

| Точка монтирования | Размер | Тип |
|-------------------|--------|-----|
| `/boot/efi` | 512 MB | EFI System Partition |
| `/boot` | 1 GB | ext2 |
| `[SWAP]` | 2 GB | swap |
| `/` | 30 GB | ext4 |




Рисунок 2 - Разбиение системного диска

![alt text](photos/image_2.png)

*На рисунке выше показана структура разделов на системном диске.*



**Шаг 3:** На втором диске (`/dev/vdb`)  - создадим раздел /pg_data.

*Как показано на скриншоте.*

---

### 2.2. Server2 - Ручное добавление диска

На втором сервере Debian уже установлен. Добавим второй диск и создадим файловую систему.

**Шаг 1:** Подключитесь к серверу и проверьте доступные диски:

```bash
lsblk
```
![alt text](photos/image_3.png)

*На скриншоте видно два диска: vda (системный) и vdb (новый, 30GB).*

**Шаг 2:** Создайте раздел на втором диске

```bash
sudo fdisk /dev/vdb
```
В интерактивном режиме выполните команды:

| Точка монтирования |  | Тип |
|-------------------|--------|-----|
| `n` |  | # создать новый раздел |
| `p` | | # primary partition |
| `1` | | # номер раздела 1 |
| `[Enter]` | | # первый сектор по умолчанию |
| `[Enter]` | | # последний сектор по умолчанию |
 `w` | | # записать изменения |

**Шаг 3:** Создайте файловую систему ext4:

```bash
sudo mkfs.ext4 /dev/vdb1
```
**Шаг 4:** Создайте точку монтирования и смонтируйте диск:
```bash
sudo mkdir -p /pg_data
sudo mount /dev/vdb1 /pg_data
```
**Шаг 5:** Добавьте запись в /etc/fstab для автоматического монтирования:
```bash
echo "UUID=$UUID /pg_data ext4 defaults 0 2" | sudo tee -a /etc/fstab
```

**Шаг 6:** Проверьте монтирование:
```bash
df -h /pg_data
mount | grep pg_data
```

## 3. Подготовка проекта Ansible

### 3.1. Создание структуры проекта

Создайте директорию для проекта:

```bash
mkdir -p ~/KMB-v-adminstvo/Velikiy_PostgreSQL/Task_0
cd ~/KMB-v-adminstvo/Velikiy_PostgreSQL/Task_0
```

Создайте структуру каталогов:

```bash
mkdir -p group_vars/postgres_servers
touch ansible.cfg inventory.ini postgresql_install.yml .gitignore
```

```
Task_0/
├── .gitignore                           # Исключения для Git
├── .vault_pass                          # 🔒 Пароль Vault (НЕ КОММИТИТЬ!)
├── ansible.cfg                          # Настройки Ansible
├── inventory.ini                        # Список хостов
├── postgresql_install.yml               # Playbook
├── README.md                            # Эта документация
├── photos/                         # Папка для скриншотов
│   ├── image_1.png
│   ├── image_2.png
│   └── ...
└── group_vars/
    └── postgres_servers/
        └── vault.yml                    # 🔒 Зашифрованные секреты
```

### 3.2. Создание файла .gitignore

Создайте файл `.gitignore` для исключения чувствительных данных из Git:

```bash
cat > .gitignore << 'EOF'
# Никогда не коммитьте эти файлы!
.vault_pass
*.key
*.pem
.env
__pycache__/
*.pyc
.DS_Store
*.swp
.swo
EOF
```

**Проверьте содержимое:**

```bash
cat .gitignore
```


---

## 4. Настройка Ansible Vault

### 4.1. Создание файла с паролем Vault

Создайте файл `.vault_pass` с паролем для шифрования:

```bash
# Генерация случайного пароля
openssl rand -base64 32 > .vault_pass

# Или создайте вручную
echo "MySuperSecretVaultPassword123!" > .vault_pass

# Установите безопасные права
chmod 600 .vault_pass
```



**Важно:** Файл `.vault_pass` никогда не должен попадать в Git репозиторий!

### 4.2. Проверка прав доступа

```bash
ls -la .vault_pass
```

*Права должны быть `600` (только владелец может читать/писать).*

### 4.3. Создание файла с секретами

Создайте файл `group_vars/postgres_servers/vault.yml` с чувствительными данными:

```bash
cat > group_vars/postgres_servers/vault.yml << 'EOF'
---
ansible_become_password: "YourSudoPassword123"
postgresql_password: "PostgresDBPassword456"
EOF
```


### 4.4. Шифрование файла

Зашифруйте файл с секретами:

```bash
ansible-vault encrypt group_vars/postgres_servers/vault.yml
```

Введите пароль дважды при запросе:

![Шифрование файла](photos/image_4.png)

### 4.5. Проверка шифрования

Проверьте, что файл зашифрован:

```bash
cat group_vars/postgres_servers/vault.yml
```

Вы должны увидеть текст, начинающийся с `$ANSIBLE_VAULT;1.1;AES256`:

![alt text](photos/image_5.png)


### 4.6. Просмотр зашифрованного файла

Для просмотра содержимого:

```bash
ansible-vault view group_vars/postgres_servers/vault.yml --ask-vault-pass
```


### 4.7. Редактирование зашифрованного файла

Для редактирования:

```bash
ansible-vault edit group_vars/postgres_servers/vault.yml --ask-vault-pass
```


### 4.8. Смена пароля Vault (при необходимости)

```bash
ansible-vault rekey group_vars/postgres_servers/vault.yml
```

Вас попросят ввести:
1. Старый пароль (для расшифровки)
2. Новый пароль (для шифрования)


---

## 5. Конфигурационные файлы

### 5.1. Файл ansible.cfg

Создайте файл `ansible.cfg` с базовыми настройками:

```bash
cat > ansible.cfg << 'EOF'
[defaults]
host_key_checking = False
inventory = inventory.ini
roles_path = ./roles

[privilege_escalation]
become = True
become_method = sudo
become_user = root
become_ask_pass = False
EOF
```

**Проверьте содержимое:**

```bash
cat ansible.cfg
```

**Объяснение параметров:**

| Параметр | Значение | Описание |
|----------|----------|----------|
| `host_key_checking` | False | Не проверять SSH ключи (для тестовой среды) |
| `inventory` | inventory.ini | Файл с хостами по умолчанию |
| `deprecation_warnings` | False | Скрыть предупреждения о устаревших функциях |
| `become` | True | Автоматически повышать привилегии через sudo |

### 5.2. Файл inventory.ini

Создайте файл `inventory.ini` со списком хостов:

```bash
cat > inventory.ini << 'EOF'
[postgres_servers]
server1 ansible_host=192.168.122.20 ansible_user=urahoy-2 ansible_become=yes
server2 ansible_host=192.168.122.75 ansible_user=urahoy-1 ansible_become=yes

[postgres_servers:vars]
ansible_become_method=sudo
ansible_python_interpreter=/usr/bin/python3
EOF
```


**Проверьте содержимое:**

```bash
cat inventory.ini
```


**Объяснение:**

| Параметр | Описание |
|----------|----------|
| `[postgres_servers]` | Имя группы хостов |
| `server1`, `server2` | Имена хостов (как в `/etc/hosts` или DNS) |
| `ansible_host` | IP-адрес сервера |
| `ansible_user` | Пользователь для SSH подключения |
| `ansible_become=yes` | Использовать sudo для повышения привилегий |

### 5.3. Проверка подключения к хостам

Проверьте подключение к серверам:

```bash
ansible -i inventory.ini all -m ping --ask-vault-pass
```

Если видите `SUCCESS` - всё настроено правильно!

### 5.4. Проверка информации о хостах

Получите информацию о серверах:

```bash
ansible -i inventory.ini all -m setup --ask-vault-pass | less
```

Или конкретный факт:

```bash
ansible -i inventory.ini all -m ansible.builtin.setup -a "filter=ansible_distribution*" --ask-vault-pass
```


### 5.5. Проверка переменных из Vault

Убедитесь, что переменные из vault.yml загружаются:

```bash
ansible -i inventory.ini all -m debug -a "var=ansible_become_password" --ask-vault-pass
```


*Должно показать значение пароля (не null).*

---

## 6. Playbook для установки PostgreSQL

### 6.1. Создание файла playbook

Создайте файл `postgresql_install.yml`:

```bash
nano postgresql_install.yml
```

Или используйте VScode.


### 6.2. Полный текст playbook

Вставьте следующий код в файл `postgresql_install.yml`:

```yaml
---
- name: Install and initialize PostgreSQL 16
  hosts: postgres_servers
  become: true
  vars:
    postgresql_version: "16"
    pg_data_dir: "/pg_data/16"
    pg_conf_dir: "/etc/postgresql/{{ postgresql_version }}/main"

  tasks:
    # ========================================================================
    # 1. Подготовка репозитория PostgreSQL
    # ========================================================================
    - name: Install required packages for adding repository
      apt:
        name:
          - gnupg
          - curl
          - apt-transport-https
          - ca-certificates
        state: present
        update_cache: true

    - name: Create directory for APT keyrings
      file:
        path: /etc/apt/keyrings
        state: directory
        mode: '0755'

    - name: Download PostgreSQL repository GPG key
      get_url:
        url: https://www.postgresql.org/media/keys/ACCC4CF8.asc
        dest: /etc/apt/keyrings/postgresql.asc
        mode: '0644'

    - name: Add PostgreSQL APT repository
      apt_repository:
        repo: "deb [signed-by=/etc/apt/keyrings/postgresql.asc] http://apt.postgresql.org/pub/repos/apt {{ ansible_facts['distribution_release'] }}-pgdg main"
        state: present
        filename: postgresql

    - name: Update apt cache after adding repository
      apt:
        update_cache: true
        cache_valid_time: 3600

    # ========================================================================
    # 2. Установка пакетов PostgreSQL
    # ========================================================================
    - name: Install PostgreSQL packages
      apt:
        name:
          - postgresql
          - postgresql-contrib
          - postgresql-{{ postgresql_version }}
          - postgresql-client-{{ postgresql_version }}
        state: present

    # ========================================================================
    # 3. Подготовка директории данных
    # ========================================================================
    - name: Create PostgreSQL data directory
      file:
        path: "{{ pg_data_dir }}"
        state: directory
        owner: postgres
        group: postgres
        mode: '0700'

    - name: Ensure data directory ownership
      file:
        path: "{{ pg_data_dir }}"
        owner: postgres
        group: postgres
        mode: '0700'
        recurse: true

    # ========================================================================
    # 4. Удаление кластера по умолчанию (если есть)
    # ========================================================================
    - name: Check if default cluster exists
      command: pg_lsclusters
      register: cluster_check
      changed_when: false
      failed_when: false

    - name: Stop default PostgreSQL cluster if running
      command: pg_ctlcluster {{ postgresql_version }} main stop
      when: cluster_check.stdout is search('main')
      ignore_errors: true

    - name: Drop default cluster
      command: pg_dropcluster {{ postgresql_version }} main --stop
      when: cluster_check.stdout is search('main')
      ignore_errors: true

    # ========================================================================
    # 5. Создание кластера с кастомной директорией
    # ========================================================================
    - name: Create new cluster with custom data directory
      command: >
        pg_createcluster {{ postgresql_version }} main
        -d {{ pg_data_dir }}
        -e UTF8
        --locale=C
      args:
        creates: "{{ pg_conf_dir }}/postgresql.conf"

    # ========================================================================
    # 6. Настройка postgresql.conf
    # ========================================================================
    - name: Configure postgresql.conf - listen_addresses
      lineinfile:
        path: "{{ pg_conf_dir }}/postgresql.conf"
        regexp: "^#?listen_addresses"
        line: "listen_addresses = '*'"
        state: present

    - name: Configure postgresql.conf - port
      lineinfile:
        path: "{{ pg_conf_dir }}/postgresql.conf"
        regexp: "^#?port"
        line: "port = 5432"
        state: present

    - name: Configure postgresql.conf - data_directory
      lineinfile:
        path: "{{ pg_conf_dir }}/postgresql.conf"
        regexp: "^#?data_directory"
        line: "data_directory = '{{ pg_data_dir }}'"
        state: present

    # ========================================================================
    # 7. Настройка pg_hba.conf
    # ========================================================================
    - name: Configure pg_hba.conf for access
      blockinfile:
        path: "{{ pg_conf_dir }}/pg_hba.conf"
        marker: "# {mark} ANSIBLE MANAGED BLOCK"
        block: |
          local   all             postgres                                peer
          local   all             all                                     peer
          host    all             all             127.0.0.1/32            scram-sha-256
          host    all             all             ::1/128                 scram-sha-256
          host    all             all             0.0.0.0/0               scram-sha-256

    # ========================================================================
    # 8. Запуск службы PostgreSQL
    # ========================================================================
    - name: Remove unused PostgreSQL 18 cluster
      command: pg_dropcluster 18 main --stop
      ignore_errors: true

    - name: Start PostgreSQL cluster
      command: pg_ctlcluster {{ postgresql_version }} main start

    - name: Enable PostgreSQL autostart
      systemd:
        name: postgresql
        enabled: true

    - name: Wait for PostgreSQL to be ready
      wait_for:
        port: 5432
        timeout: 30

    - name: Verify PostgreSQL is running
      command: pg_isready
      register: pg_status
      changed_when: false

    - name: Display PostgreSQL status
      debug:
        msg: "PostgreSQL is {{ 'running' if pg_status.rc == 0 else 'not running' }}"

    # ========================================================================
    # 9. Установка пароля для пользователя postgres
    # ========================================================================
    - name: Set password for postgres user
      become: true
      shell: |
        su - postgres -c "psql -c \"ALTER USER postgres WITH PASSWORD '{{ postgresql_password }}'\""
      no_log: true
```


### 6.3. Синтаксическая проверка playbook

Перед запуском проверьте синтаксис:

```bash
ansible-playbook --syntax-check -i inventory.ini postgresql_install.yml
```


Если видите `playbook: postgresql_install.yml` без ошибок - синтаксис верный!

### 6.4. Проверка списка задач

Посмотрите список задач без выполнения:

```bash
ansible-playbook -i inventory.ini postgresql_install.yml --list-tasks --ask-vault-pass
```


---

## 7. Запуск и проверка

### 7.1. Запуск playbook

Запустите установку PostgreSQL:

```bash
ansible-playbook -i inventory.ini postgresql_install.yml --ask-vault-pass
```

Введите пароль Vault при запросе.

### 7.2. Процесс выполнения

Playbook выполнит все задачи последовательно:

![alt text](photos/image_6.png)

*На скриншоте показан процесс выполнения задач. Дождитесь завершения.*

### 7.3. Результат выполнения

После завершения вы увидите итоговый отчёт:


**Расшифровка PLAY RECAP:**

| Поле | Значение | Норма |
|------|----------|-------|
| `ok` | Успешно выполненные задачи | Любое число |
| `changed` | Задачи, которые внесли изменения | Любое число |
| `unreachable` | Недоступные хосты | **Должно быть 0** |
| `failed` | Ошибочные задачи | **Должно быть 0** |
| `skipped` | Пропущенные задачи | Любое число |
| `rescued` | Исправленные ошибки | 0 или больше |
| `ignored` | Игнорируемые ошибки | 0 или больше |

**Успешное выполнение:** `failed=0` и `unreachable=0` на всех хостах!

---

## 8. Проверка установки

### 8.1. Проверка статуса кластеров

Проверьте статус кластеров PostgreSQL:

```bash
ansible -i inventory.ini all -a "pg_lsclusters" --ask-vault-pass
```

**Ожидаемый результат:**
```
Ver Cluster Port Status  Owner    Data directory
16  main    5432 online  postgres /pg_data/16
```

![alt text](photos/image_7.png)

### 8.2. Проверка версии PostgreSQL

```bash
ansible -i inventory.ini all -a "psql --version" --ask-vault-pass
```


### 8.3. Проверка директории данных

```bash
ansible -i inventory.ini all -a "ls -la /pg_data/16/" --ask-vault-pass
```


### 8.4. Проверка конфигурации listen_addresses

Проверьте, что PostgreSQL слушает все интерфейсы:

```bash
ansible -i inventory.ini all -a "grep listen_addresses /etc/postgresql/16/main/postgresql.conf" --ask-vault-pass
```

![alt text](photos/image_8.png)

**Должно быть:** `listen_addresses = '*'`



### 8.5. Подключение к БД и проверка версии

Подключитесь к PostgreSQL и проверьте версию:

```bash
ansible -i inventory.ini all -m shell -a "sudo -u postgres psql -c 'SELECT version();'" --ask-vault-pass
```

### 8.6. Проверка data_directory

```bash
ansible -i inventory.ini all -m shell -a "sudo -u postgres psql -c 'SHOW data_directory;'" --ask-vault-pass
```

![alt text](photos/image_9.png)

**Должно быть:** `/pg_data/16`

### 8.7. Проверка подключения с паролем

Проверьте, что пароль установлен правильно:

```bash
ansible -i inventory.ini all -m shell -a "PGPASSWORD='ваш_пароль' psql -h localhost -U postgres -c 'SELECT now();'" --ask-vault-pass
```


### 8.8. Проверка статуса службы systemd

```bash
ansible -i inventory.ini all -a "systemctl status postgresql" --ask-vault-pass
```


**Должно быть:** `active (running)`

---

## 9. Устранение неполадок

### 9.1. Ошибка: "Permission denied (publickey,password)"

**Проблема:** Не настроен SSH доступ.

**Решение:**
```bash
# Скопируйте SSH ключ на серверы
ssh-copy-id urahoy@192.168.122.19
ssh-copy-id urahoy@192.168.122.75

# Или проверьте пароль
ansible -i inventory.ini all -m ping -k
```

### 9.2. Ошибка: "sudo: требуется указать пароль"

**Проблема:** Не настроен пароль sudo в vault.yml

**Решение:**
```bash
# Отредактируйте vault.yml
ansible-vault edit group_vars/postgres_servers/vault.yml --ask-vault-pass

# Добавьте строку:
# ansible_become_password: "ВашSudoПароль"
```


### 9.3. Ошибка: "non-zero return code" при initdb

**Проблема:** initdb запускается от root.

**Решение:** Убедитесь, что используете `su - postgres -c` для запуска initdb (как в playbook).

### 9.4. Ошибка: "specified cluster does not exist"

**Проблема:** Попытка удалить несуществующий кластер.

**Решение:** Это нормально. Задача имеет `ignore_errors: true` и не останавливает выполнение.


### 9.5. Ошибка: "chmod: неверный режим"

**Проблема:** Проблемы с ACL на файловой системе.

**Решение:** Добавьте в `ansible.cfg`:
```ini
[defaults]
allow_world_readable_tmpfiles = True
```

### 9.6. PostgreSQL не запускается

**Проверка логов:**
```bash
ansible -i inventory.ini all -a "tail -50 /var/log/postgresql/postgresql-16-main.log" --ask-vault-pass
```


**Проверка статуса службы:**
```bash
ansible -i inventory.ini all -a "systemctl status postgresql" --ask-vault-pass
```

### 9.7. Не могу подключиться удалённо

**Проверьте firewall:**
```bash
# На сервере
sudo ufw allow 5432/tcp
sudo ufw status
```

**Проверьте pg_hba.conf:**
```bash
ansible -i inventory.ini all -a "cat /etc/postgresql/16/main/pg_hba.conf" --ask-vault-pass
```

Убедитесь, что есть строка:
```
host    all             all             0.0.0.0/0               scram-sha-256
```

---

## 10. Контрольный чек-лист

### 10.1. Подготовка инфраструктуры

- [ ] На Server1: второй диск добавлен при установке
- [ ] На Server2: второй диск размечен и отформатирован
- [ ] На обоих серверах: `/pg_data` смонтирован
- [ ] Запись в `/etc/fstab` добавлена для авто-монтирования
- [ ] Права на `/pg_data` установлены correctly (postgres:postgres, 0700)

### 10.2. Настройка Ansible

- [ ] SSH доступ работает без пароля
- [ ] Файл `.vault_pass` создан и защищён (chmod 600)
- [ ] Файл `.vault_pass` добавлен в `.gitignore`
- [ ] Файл `vault.yml` создан и зашифрован
- [ ] `ansible.cfg` настроен правильно
- [ ] `inventory.ini` содержит правильные IP-адреса
- [ ] `ansible -m ping` возвращает SUCCESS

### 10.3. Установка PostgreSQL

- [ ] Playbook прошёл синтаксическую проверку
- [ ] Playbook выполнился без ошибок (failed=0)
- [ ] PostgreSQL работает (status online)
- [ ] Данные хранятся в `/pg_data/16`
- [ ] Можно подключиться с паролем
- [ ] Порт 5432 открыт и слушает

### 10.4. Финальная проверка

```bash
# Проверка всех кластеров
ansible -i inventory.ini all -a "pg_lsclusters" --ask-vault-pass

# Проверка версии
ansible -i inventory.ini all -a "psql --version" --ask-vault-pass

# Проверка директории
ansible -i inventory.ini all -a "ls -la /pg_data/16/" --ask-vault-pass
```

---

## 11. Итоговая структура проекта

```
Task_0/
├── .gitignore                           # Исключения для Git
├── .vault_pass                          # 🔒 Пароль Vault (НЕ КОММИТИТЬ!)
├── ansible.cfg                          # Настройки Ansible
├── inventory.ini                        # Список хостов
├── postgresql_install.yml               # Playbook
├── README.md                            # Эта документация
├── screenshots/                         # Папка для скриншотов
│   ├── 01_partitioning_method.png
│   ├── 02_system_disk_partition.png
│   └── ...
└── group_vars/
    └── postgres_servers/
        └── vault.yml                    # 🔒 Зашифрованные секреты
```


---

## 12. Полезные команды

### 12.1. Управление Vault

```bash
# Просмотр зашифрованного файла
ansible-vault view group_vars/postgres_servers/vault.yml --ask-vault-pass

# Редактирование
ansible-vault edit group_vars/postgres_servers/vault.yml --ask-vault-pass

# Шифрование нового файла
ansible-vault encrypt file.yml --ask-vault-pass

# Расшифровка (навсегда)
ansible-vault decrypt group_vars/postgres_servers/vault.yml --ask-vault-pass

# Смена пароля
ansible-vault rekey group_vars/postgres_servers/vault.yml
```

### 12.2. Запуск playbook

```bash
# Обычный запуск
ansible-playbook -i inventory.ini postgresql_install.yml --ask-vault-pass

# С проверкой (dry-run)
ansible-playbook -i inventory.ini postgresql_install.yml --check --diff --ask-vault-pass

# Запуск конкретной задачи
ansible-playbook -i inventory.ini postgresql_install.yml --start-at-task="Install PostgreSQL packages" --ask-vault-pass

# Запуск на конкретном хосте
ansible-playbook -i inventory.ini postgresql_install.yml --limit server1 --ask-vault-pass
```

### 12.3. Администрирование PostgreSQL

```bash
# Создание базы данных
ansible -i inventory.ini all -m shell -a "sudo -u postgres createdb myapp" --ask-vault-pass

# Создание пользователя
ansible -i inventory.ini all -m shell -a "sudo -u postgres psql -c \"CREATE USER myuser WITH PASSWORD 'mypass';\"" --ask-vault-pass

# Резервное копирование
ansible -i inventory.ini all -m shell -a "sudo -u postgres pg_dump -Fc myapp > /backup/myapp.dump" --ask-vault-pass

# Восстановление
ansible -i inventory.ini all -m shell -a "sudo -u postgres pg_restore -d myapp /backup/myapp.dump" --ask-vault-pass

# Список баз данных
ansible -i inventory.ini all -m shell -a "sudo -u postgres psql -c '\l'" --ask-vault-pass
```

---

## 13. Дополнительные ресурсы

### Документация

- [Ansible Vault Documentation](https://docs.ansible.com/ansible/latest/user_guide/vault.html)
- [PostgreSQL 16 Documentation](https://www.postgresql.org/docs/16/)
- [Ansible Best Practices](https://docs.ansible.com/ansible/latest/user_guide/playbooks_best_practices.html)

### Полезные ссылки

- [Debian PostgreSQL Wiki](https://wiki.debian.org/PostgreSQL)
- [PostgreSQL Configuration Reference](https://www.postgresql.org/docs/current/runtime-config.html)
- [Ansible Galaxy - PostgreSQL Role](https://galaxy.ansible.com/geerlingguy/postgresql)

---

## Заключение

Поздравляем! 🎉

Вы успешно:
- ✅ Настроили инфраструктуру с отдельными дисками для данных
- ✅ Реализовали безопасное хранение паролей через Ansible Vault
- ✅ Автоматизировали установку и настройку PostgreSQL 16
- ✅ Настроили удалённый доступ к базе данных
- ✅ Создали идемпотентный playbook для повторного развёртывания

Теперь ваша база данных готова к работе! 🚀

---

*Документ подготовлен в рамках курса "КМБ в администво"*  
*Версия: 1.0 | Дата: 2026 | Автор: Товпеко Глеб Вадимович (@glebffff, telegram)*

