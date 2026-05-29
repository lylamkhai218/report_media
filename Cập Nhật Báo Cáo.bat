@echo off
chcp 65001 > nul
echo ----------------------------------------------------
echo ĐANG CẬP NHẬT BÁO CÁO GIỮ CHÂN VIDEO (FACEBOOK)...
echo ----------------------------------------------------
echo.
"C:\Users\OS\AppData\Local\Python\bin\python.exe" "d:\T&TVina\Report\create_report.py"
echo.
echo ----------------------------------------------------
echo Đã cập nhật thành công!
echo Nhấn phím bất kỳ để đóng cửa sổ này.
echo ----------------------------------------------------
pause > nul
