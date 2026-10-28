@echo off
REM Script chày thuật toán lập thời khoá biểu
REM Cách dùng:
REM   run_schedule.bat                 -> chày với file cấu hình mặc đọn (GaSchedule.json)
REM   run_schedule.bat ten_file.json  -> chày với file cấu hình tùy chỉnh
REM   run_schedule.bat ten_file.json --no-serve -> tạo báo cáo HTML trong thư mục tấm, không mội mây chệ

cd /d "%~dp0"
python ConsoleApp.py %*
