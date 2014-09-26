#!/usr/bin/env python3

import sys, tkinter

from tc import producer, viewer, server

def main():
    if len(sys.argv) == 1:
        master = tkinter.Tk()
        master.title('Telecorpo')

        def command(func):
            def inner():
                master.destroy()
                func()
            return inner

        producer_btn = tkinter.Button(master, text='Producer', command=command(producer.main))
        producer_btn.pack(expand=True, fill='both')
        
        viewer_btn = tkinter.Button(master, text='Viewer', command=command(viewer.main))
        viewer_btn.pack(expand=True, fill='both')

        master.mainloop()

    elif len(sys.argv) == 2:
        if sys.argv[1] == 'server':
            server.main()
        elif sys.argv[1] == 'producer':
            producer.main()
        elif sys.argv[1] == 'viewer':
            viewer.main()
