Option Explicit
Dim fso, shell, root, entry, errText
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
root = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = root

' Prefer the console-free launcher, but never fail silently: if it is missing
' (or Python cannot start) say so in a dialog instead of doing nothing.
entry = root & "\run_black.pyw"
If Not fso.FileExists(entry) Then entry = root & "\app.py"
If Not fso.FileExists(entry) Then
    MsgBox "Cannot find run_black.pyw or app.py in:" & vbCrLf & root & vbCrLf & vbCrLf & _
           "Please check that the folder is complete.", vbCritical, "Black failed to start"
    WScript.Quit 1
End If

On Error Resume Next
shell.Run "pythonw.exe " & Chr(34) & entry & Chr(34), 0, False
If Err.Number <> 0 Then
    errText = Err.Description
    Err.Clear
    ' pythonw.exe may be missing from PATH: retry with the console interpreter.
    shell.Run "python.exe " & Chr(34) & entry & Chr(34), 1, False
    If Err.Number <> 0 Then
        MsgBox "Black failed to start:" & vbCrLf & errText & vbCrLf & Err.Description & vbCrLf & vbCrLf & _
               "Run install dependencies first, and make sure Python is on PATH.", vbCritical, "Black failed to start"
    End If
End If