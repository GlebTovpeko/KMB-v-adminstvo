#!/usr/bin/python
from ansible.module_utils.basic import AnsibleModule
import os
import re

def main():
    module = AnsibleModule(
        argument_spec=dict(
            port=dict(type='int', required=True),
            config_path=dict(type='str', default='/etc/nginx/nginx.conf')
        ),
        supports_check_mode=True  # включаем поддержку check mode
    )
    
    port = module.params['port']
    path = module.params['config_path']
    changed = False
    
    # Проверяем существование файла
    if not os.path.exists(path):
        module.fail_json(msg=f"File {path} not found")
    
    # Читаем файл
    with open(path, 'r') as f:
        content = f.read()
    
    # Заменяем ВСЕ возможные варианты
    new_content = content
    
    # 1. Формат listen 10.23.68.202:80;
    new_content = re.sub(r'(listen\s+\d+\.\d+\.\d+\.\d+):\d+', r'\g<1>:' + str(port), new_content)
    
    # 2. Формат listen 127.0.0.1:80;
    new_content = re.sub(r'(listen\s+127\.0\.0\.1):\d+', r'\g<1>:' + str(port), new_content)
    
    # 3. Формат listen 80;
    new_content = re.sub(r'(listen\s+)(\d+)(;|\s)', r'\g<1>' + str(port) + r'\g<3>', new_content)
    
    # 4. Формат listen [::]:80;
    new_content = re.sub(r'(listen\s+\[::\]):\d+', r'\g<1>:' + str(port), new_content)
    
    # Проверяем, изменилось ли содержимое
    if new_content != content:
        changed = True
        
        # Если это check mode, не пишем файл
        if not module.check_mode:
            # Создаем бэкап
            backup_path = path + ".backup"
            with open(backup_path, 'w') as f:
                f.write(content)
            
            # Записываем новый конфиг
            with open(path, 'w') as f:
                f.write(new_content)
            
            module.exit_json(
                changed=True,
                msg=f"Port changed to {port}",
                backup_file=backup_path
            )
        else:
            # В check mode просто сообщаем, что изменения будут
            module.exit_json(changed=True, msg=f"Would change port to {port}")
    
    module.exit_json(changed=False, msg="No changes needed")

if __name__ == '__main__':
    main()