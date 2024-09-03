import time


def _window_write_bat(bat_path, py_path, *py_args):
    args_str = ' '.join(py_args)

    script = f"""
    @echo off
    python "{py_path}" {args_str}
    """
    with open(bat_path, 'w') as bat:
        bat.write(script)

    time.sleep(0.1)


def _window_write_service(service_name, bat_path):
    script = f"""
    @echo off
    setlocal
    
    echo Checking for admin privileges...
    
    net session >nul 2>&1
    if '%errorlevel%' NEQ '0' (
        echo Requesting administrative privileges...
         goto UACPrompt
    ) else (
        goto gotAdmin
    )   
    
    :UACPrompt
        echo Set UAC = CreateObject^("Shell.Application"^) > "%temp%\getadmin.vbs"
        echo UAC.ShellExecute "%~s0", "", "", "runas", 1 >> "%temp%\getadmin.vbs"

        "%temp%\getadmin.vbs"
        exit /B
        
    :gotAdmin
        SET SERVICE_NAME="{service_name}"
    
        echo Running %SERVICE_NAME% service creation...
        sc create %SERVICE_NAME% binPath="{bat_path}" start= auto
    
        if errorlevel 1 (
            echo Failing Registration %SERVICE_NAME% Service 
            exit /b 1
        ) else (
            echo Success Registration %SERVICE_NAME% Service 
            exit /b 0
        )
    """

    temp_path = 'temp_reg.bat'
    with open(temp_path, 'w') as bat:
        bat.write(script)

    time.sleep(0.1)

    return temp_path
