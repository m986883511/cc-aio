import urwid

top_layer = None
top_loop = None


def exit_program(button):
    raise urwid.ExitMainLoop()


def return_last(button):
    top_layer.return_fn()
