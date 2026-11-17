Option Explicit
Dim fso, shell, root
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root
On Error Resume Next
shell.Run "pythonw.exe " & Chr(34) & root & "\run_black.pyw" & Chr(34), 0, False
If Err.Number <> 0 Then
    MsgBox "Black failed to start. Please run install_dependencies.bat first.", vbCritical, "Black"
End If
