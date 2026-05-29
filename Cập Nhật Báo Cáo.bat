@echo off
chcp 65001 > nul
echo ----------------------------------------------------
echo ĐANG CẬP NHẬT BÁO CÁO GIỮ CHÂN VIDEO (FACEBOOK)...
echo ----------------------------------------------------
echo.
"C:\Users\OS\AppData\Local\Python\bin\python.exe" "d:\T&TVina\Report\create_report.py"
echo.
echo ----------------------------------------------------
echo ĐANG TỰ ĐỘNG ĐẨY BÁO CÁO LÊN GITHUB (NHÁNH MAIN)...
echo ----------------------------------------------------
git add .
git commit -m "Auto-update report: %date% %time%"
git push origin main
echo.
echo ----------------------------------------------------
echo ĐANG XUẤT BẢN LÊN WEBSITE (GITHUB PAGES)...
echo ----------------------------------------------------
node "d:\T&TVina\Report\node_modules\gh-pages\bin\gh-pages.js" -d "d:\T&TVina\Report"
echo.
echo ----------------------------------------------------
echo Đã cập nhật thành công và đồng bộ lên link web!
echo Nhấn phím bất kỳ để đóng cửa sổ này.
echo ----------------------------------------------------
pause > nul
