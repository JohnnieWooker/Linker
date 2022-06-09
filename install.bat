"C:\Program Files\7-Zip\7z.exe" a -tzip "Linker.zip" "Linker"

xcopy "Linker" "%appdata%\Blender Foundation\Blender\2.92\scripts\addons\Linker" /E/C/Y/I
xcopy "Linker" "%appdata%\Blender Foundation\Blender\2.93\scripts\addons\Linker" /E/C/Y/I
xcopy "Linker" "%appdata%\Blender Foundation\Blender\2.93\scripts\addons\Linker" /E/C/Y/I
xcopy "Linker" "%appdata%\Blender Foundation\Blender\3.1\scripts\addons\Linker" /E/C/Y/I
xcopy "Linker" "%appdata%\Blender Foundation\Blender\3.2\scripts\addons\Linker" /E/C/Y/I

if %errorlevel%==1 pause