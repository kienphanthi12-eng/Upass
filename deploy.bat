@echo off
echo ===================================================
echo   U-PASS - Dịch vụ Deploy Nhanh lên Vercel
echo ===================================================
echo.
echo Dang chay kiem tra va tai len ma nguon...
vercel.cmd --prod --yes
echo.
echo ===================================================
echo   Deploy hoan tat! Truy cap web tai: https://upass.io.vn
echo ===================================================
pause
