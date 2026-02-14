@Echo Off
chcp 65001 >nul 2>&1 
SETLOCAL ENABLEDELAYEDEXPANSION
title 提取所有子目录文件 

:GTBegin
@echo 将以 剪切 方式提取所有子目录文件，确定继续？(y/n)
set /p GTConfirm=
if "%GTConfirm%"=="y" goto GTYES
if "%GTConfirm%"=="Y" goto GTYES
if "%GTConfirm%"=="n" goto GTNO
if "%GTConfirm%"=="N" goto GTNO
echo 请输入正确的指令
pause >nul
goto GTBegin

:GTYES
REM 获取所有子目录
for /f "delims=" %%d in ('dir /b /ad') do (
    if /i not "%%d"=="." if /i not "%%d"==".." (
        echo.
        echo 正在处理子目录: %%d
        set /p processDir="是否要剪切此目录中的文件？(y/n): "
        if /i "!processDir!"=="y" (
            echo 正在剪切文件...
            for /f "delims=" %%a in ('dir "%%d" /b /s /a-d 2^>nul') do (
                set "filename=%%~nxa"
                set "filepath=%%a"
                
                REM 检查目标位置是否已存在同名文件
                if exist "%~dp0!filename!" (
                    echo.
                    echo 发现同名文件: !filename!
                    choice /c YNR /m "请选择操作：覆盖(Y)/重命名(R)/跳过(N)"
                    if errorlevel 3 (
                        echo 跳过文件: !filename!
                    ) else if errorlevel 2 (
                        REM 重命名文件
                        set /p newname="请输入新文件名（不含路径）: "
                        if "!newname!"=="" (
                            echo 未输入新文件名，跳过: !filename!
                        ) else (
                            move /y "!filepath!" "%~dp0!newname!" >nul
                            if !errorlevel! equ 0 (
                                echo 已移动并重命名: !filename! ^>^> !newname!
                            ) else (
                                echo 移动失败: !filename!
                            )
                        )
                    ) else if errorlevel 1 (
                        REM 覆盖文件
                        move /y "!filepath!" "%~dp0" >nul
                        if !errorlevel! equ 0 (
                            echo 已覆盖: !filename!
                        ) else (
                            echo 覆盖失败: !filename!
                        )
                    )
                ) else (
                    REM 没有同名文件，直接移动
                    move /y "!filepath!" "%~dp0" >nul
                    if !errorlevel! equ 0 (
                        echo 已移动: !filename!
                    ) else (
                        echo 移动失败: !filename!
                    )
                )
            )
            REM 检查目录是否为空，如果为空则删除
            dir "%%d" /b 2>nul | findstr . >nul || (
                echo 目录已空，正在删除: %%d
                rd "%%d" 2>nul
            )
        ) else (
            echo 跳过目录: %%d
        )
    )
)

echo.
echo :) 搞定
pause >nul
exit

:GTNO
exit