@echo off
set HOST=root@194.77.71.29
set DIR=/var/www/lifeos

echo Загружаем файлы...
scp main.py aiogram_bot.py .env %HOST%:%DIR%/
scp -r lifeos lifeos_bot static %HOST%:%DIR%/

echo Перезапускаем сервисы...
ssh %HOST% "rm -f %DIR%/static/app.js && systemctl restart lifeos lifeos-bot"

echo Готово!
pause
