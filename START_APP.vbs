Set objShell = CreateObject("WScript.Shell")
Set objFSO = CreateObject("Scripting.FileSystemObject")

' Get the directory of this script
strScriptPath = objFSO.GetParentFolderName(WScript.ScriptFullName)

' Change to the script directory and run npm start silently
objShell.Run "cmd /c cd /d """ & strScriptPath & """ && npm start", 0, False

Set objShell = Nothing
Set objFSO = Nothing
