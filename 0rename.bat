@echo off
chcp 65001 >nul 2>&1 
setlocal enabledelayedexpansion

echo 当前目录：%cd%
echo 正在处理当前文件夹中的文件...
echo.

for %%f in (*) do (
    echo 处理文件: "%%f"
    if not "%%f"=="%~nx0" (
        if exist "%%f" (
            set "filename=%%~nf"
            set "extension=%%~xf"
            set "skip=0"
            set "reason="
            
            rem 检查是否为.bat文件
            if /i "!extension!"==".bat" (
                set "skip=1"
                set "reason=BAT文件"
            )
            
            rem 检查是否为压缩文件格式
            if /i "!extension!"==".zip" (
                set "skip=1"
                set "reason=ZIP文件"
            )
            if /i "!extension!"==".rar" (
                set "skip=1"
                set "reason=RAR文件"
            )
            if /i "!extension!"==".7z" (
                set "skip=1"
                set "reason=7Z文件"
            )
            if /i "!extension!"==".tar" (
                set "skip=1"
                set "reason=TAR文件"
            )
            if /i "!extension!"==".gz" (
                set "skip=1"
                set "reason=GZ文件"
            )
            
            rem 检查是否为分卷压缩文件（改进版）
            rem 检查.001, .002, .003等数字序列
            if "!skip!"=="0" (
                set "ext_num=!extension:~1!"
                set /a test_num=!ext_num! 2>nul
                if !errorlevel! equ 0 (
                    if !ext_num! geq 1 if !ext_num! leq 999 (
                        set "skip=1"
                        set "reason=分卷压缩文件"
                    )
                )
            )
            
            rem 检查.r00, .r01, .r02等RAR分卷
            if "!skip!"=="0" (
                if "!extension:~1,1!"=="r" (
                    set "ext_num=!extension:~2!"
                    set /a test_num=!ext_num! 2>nul
                    if !errorlevel! equ 0 (
                        if !ext_num! geq 0 if !ext_num! leq 99 (
                            set "skip=1"
                            set "reason=RAR分卷压缩文件"
                        )
                    )
                )
            )
            
            rem 检查.part1.rar, .part2.rar等分卷
            if "!skip!"=="0" (
                echo "!filename!" | findstr /i "\.part[0-9]*$" >nul
                if !errorlevel! equ 0 (
                    set "skip=1"
                    set "reason=分卷压缩文件"
                )
            )
            
            rem 检查.7z.001, .zip.001等多扩展名分卷
            if "!skip!"=="0" (
                echo "!filename!" | findstr /i "\.\(zip\|rar\|7z\)$" >nul
                if !errorlevel! equ 0 (
                    set "ext_num=!extension:~1!"
                    set /a test_num=!ext_num! 2>nul
                    if !errorlevel! equ 0 (
                        if !ext_num! geq 1 if !ext_num! leq 999 (
                            set "skip=1"
                            set "reason=分卷压缩文件"
                        )
                    )
                )
            )
            
            rem 如果不需要跳过，则重命名为.zip
            if "!skip!"=="0" (
                echo 重命名: "%%f" → "!filename!.zip"
                ren "%%f" "!filename!.zip" 2>nul
                if !errorlevel! neq 0 (
                    echo 错误: 重命名失败，可能是文件名冲突或文件正在使用
                )
            ) else (
                echo 跳过: "%%f" - 原因: !reason!
            )
        )
    ) else (
        echo 跳过自身: "%%f"
    )
)

echo.
echo 处理完成！
pause