@echo off
chcp 65001 >nul
echo ============================================
echo  WeasyPrint Windows 安装脚本
echo  用于解决 PDF 中文乱码和样式问题
echo ============================================
echo.

:: 检查是否在虚拟环境中
if defined VIRTUAL_ENV (
    echo [信息] 检测到虚拟环境: %VIRTUAL_ENV%
    echo   weasyprint 将安装到该虚拟环境中（仅当前项目可用）
    echo.
    set "PIP_CMD=pip"
) else (
    echo [警告] 未检测到虚拟环境！
    echo.
    echo   weasyprint 将安装到全局 Python，可能影响其他项目。
    echo   建议先激活项目虚拟环境再运行此脚本：
    echo.
    echo     cd %~dp0
    echo     .venv\Scripts\activate
    echo     install_weasyprint_windows.bat
    echo.
    choice /C YN /M "是否继续安装到全局 Python"
    if errorlevel 2 exit /b 0
    set "PIP_CMD=pip"
)

:: 检查 Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到 Python，请先安装 Python 3.10+
    pause
    exit /b 1
)

:: 检查是否已有 weasyprint
python -c "import weasyprint; print(f'weasyprint {weasyprint.__version__} 已安装')" >nul 2>&1
if not errorlevel 1 (
    echo [信息] weasyprint 已安装
    python -c "import weasyprint; print(f'  版本: {weasyprint.__version__}')"
    echo.
    echo 如需重装，先运行: pip uninstall weasyprint
    pause
    exit /b 0
)

echo [步骤 1/3] 安装 Python 依赖 (weasyprint)...
echo.

:: 先安装 cffi 和其他构建依赖
%PIP_CMD% install cffi pillow --quiet 2>nul

:: 安装 weasyprint
%PIP_CMD% install "weasyprint>=61.0"
if errorlevel 1 (
    echo.
    echo [警告] pip 安装 weasyprint 失败，可能是缺少 GTK 运行时
    echo.
    goto :install_gtk
)

:: 验证安装
python -c "from weasyprint import HTML; print('weasyprint 导入成功')" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [警告] weasyprint 安装成功但导入失败，可能是缺少 GTK 运行时
    echo.
    goto :install_gtk
)

echo.
echo [步骤 2/3] 验证 GTK 运行时...
python -c "import weasyprint; print(f'  weasyprint {weasyprint.__version__} 安装成功')" 2>nul
if errorlevel 1 (
    goto :install_gtk
)

echo   GTK 运行时正常
echo.
echo [步骤 3/3] 验证中文字体支持...
python -c "from weasyprint import HTML; HTML(string='<p>中文测试</p>').write_pdf()" >nul 2>&1
if errorlevel 1 (
    echo [警告] PDF 生成测试失败，请检查 GTK 运行时
) else (
    echo   中文字体渲染正常
)
echo.
echo ============================================
echo  安装完成！PDF 渲染将使用 weasyprint 引擎
echo ============================================
pause
exit /b 0

:install_gtk
echo.
echo ============================================
echo  需要安装 GTK3 运行时（WeasyPrint 依赖）
echo ============================================
echo.
echo 注意：GTK 运行时是系统级安装，所有程序共享
echo.
echo 请选择安装方式：
echo.
echo   方式一（推荐）：下载 GTK3 安装器
echo     1. 访问 https://github.com/nickvdp/gtk-win64/releases
echo     2. 下载最新的 gtk3-runtime-xxx-win64.exe
echo     3. 运行安装器，勾选 "Add to PATH"
echo     4. 安装完成后重新运行此脚本
echo.
echo   方式二：使用 MSYS2
echo     1. 安装 MSYS2: https://www.msys2.org/
echo     2. 在 MSYS2 终端执行:
echo        pacman -S mingw-w64-x86_64-gtk3 mingw-w64-x86_64-pango
echo     3. 将 C:\msys64\mingw64\bin 添加到系统 PATH
echo     4. 重新运行此脚本
echo.
echo   方式三：使用 conda
echo     conda install -c conda-forge weasyprint
echo.
echo 安装 GTK 后，重新运行此脚本验证安装
echo ============================================
pause
exit /b 1
