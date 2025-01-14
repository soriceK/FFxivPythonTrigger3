import ctypes


dll = ctypes.WinDLL('ntdll.dll')

NTSTATUS = ctypes.c_ulong
THREADINFOCLASS = ctypes.c_ulong

#: Retrieves information about the specified thread.
#:
#: https://msdn.microsoft.com/en-us/library/windows/desktop/ms684283.aspx
NtQueryInformationThread = dll.NtQueryInformationThread
NtQueryInformationThread.restype = NTSTATUS
NtQueryInformationThread.argtypes = [
    ctypes.c_void_p,
    THREADINFOCLASS,
    ctypes.c_void_p,
    ctypes.c_ulong,
    ctypes.POINTER(ctypes.c_ulong)
]
