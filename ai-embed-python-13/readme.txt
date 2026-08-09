Notes for pythonwin - Version 0.9.
Mark Hammond <MHammond@skippinet.com.au>                May 2, 1996
-------------------------------------------------------------------
This is a special readme for the version of Pythonwin shipped in
CD for the Python book.

This is the latest version of Pythonwin as at May 2.  It is likely
that by the time you read this, a newer version will exist.
The Python home page <www.python.org> has links to download instructions
for Pythonwin.  This is where you can find the latest version.
You can also find the Pythonwin FAQ at this site.

All file names in this distribution have been truncated to 8.3 format.
This is so the same version will work on Windows 3.1 and Windows NT/95.
The normal distribution for NT/95 uses the full file names.

If you are using Windows 3.1, you must have the latest Win32s.  This
can be found at <ftp://ftp.microsoft.com/Softlib/MSLFILES/PW1118.EXE">
Also, "python.exe" will NOT work on windows 3.1.  python.exe is a command 
line version of Python, but Windows 3.1 will not support 32 bit command line
programs.

RUNNING PYTHONWIN:
------------------
 You should be able to double-click on "pythonwi.exe" to start Pythonwin
 directly from the CD.

 However, for optimum performance, Pythonwin should be installed on your hard
 disk, and a "setup" process run.

INSTALLATION INSTRUCTIONS:
--------------------------
 Install shared DLLs.  MSVCRT40.DLL and MFC40.DLL must be installed
 into your system directory.
 First check if you already have these DLLs installed.  If so
 check the version you have is newer than the CD ones, and if
 so, DO NOT perform this step.
  - Windows 3.1 - "copy shared\win31\*.dll c:\windows\system"
  - Windows 95 -  "copy shared\nt95\*.dll  c:\win95\system"
  - Windows NT -  "copy shared\nt95\*.dll c:\winnt\system32"
 Of course, change the "c:\win..." to your windows path.

 Create the directory on your hard disk where you wish to have Python 
 installed.

 Using XCOPY, copy the entire Pythonwin directory structure to your
 hard disk.  Remember to include subdurectories.  This process should
 work:
 - start a command prompt.
 - change to the CD drive, and into the Pythonwin directory (ie,
   where this readme is)
 - enter the command "xcopy *.* c:\python /s", assuming you wish to
   install to c:\python.

 Remove the "shared" directories from your hard disk.  (These are no
 longer needed, as you have already installed them into your system
 directory).

 NT/95 - from a command prompt in the hard-disk Python directory, run the
 command "python scripts\regsetup.py".  On NT, you must be logged in as
 an administrator, else this will fail.

 Windows 3.1 - from file manager, select "pythonwi.exe" on the hard-disk.  
 Select the "File" menu, then "Run".  Change the command line to
 "pythonwi.exe /run scripts\regsetup.py", and press <enter>.

 Setup icons to Pythonwin.exe, python.exe, hlp files etc.

 Off you go!

- eof -