from __future__ import annotations
import string
import typing

import urwid

from pvetui.config import CONF
from cs_utils import file, execute, func


# def get_int_edit_widget(name, group=None):
#     edit = IntEdit(name, group, caption='')

#     def callback(edit_obj: IntEdit, current_value):
#         tmp = current_value or 0
#         if int(tmp)>5:
#             edit_obj.set_caption(('header',["cannot be greater than 5!", ("white", " "), ]))
#         else:
#             edit_obj.set_caption('')
#         func.set_conf_group_value(current_value, edit_obj.CONF_cfg_name, edit_obj.CONF_group_name)
#         edit_obj.update_value_to_file()

#     urwid.connect_signal(edit, 'change', callback)
#     return edit


class MyCheckBox(urwid.CheckBox):
    def __init__(self,  *args, **kwargs) -> None:
        self.origin_label = args[0]
        super().__init__(*args, **kwargs)


class TextEdit(urwid.Edit):
    def __init__(self,  caption, edit_text, call_func, **kwargs) -> None:
        self.origin_caption = caption
        if isinstance(edit_text, int):
            edit_text = str(edit_text)
        super().__init__(caption, edit_text, **kwargs)
        urwid.connect_signal(self, 'change', call_func)


class IntEdit(urwid.Edit):
    """Edit widget for integer values"""
    def __init__(self,  CONF_cfg_name, CONF_group_name=None, caption="", my_min=None, my_max=None, **kwargs) -> None:
        """
        caption -- caption markup
        default -- default edit value

        >>> IntEdit(u"", 42)
        <IntEdit selectable flow widget '42' edit_pos=2>
        """
        self.CONF_group_name = CONF_group_name
        self.CONF_cfg_name = CONF_cfg_name
        self.my_min = my_min
        self.my_max = my_max
        val = str(func.get_conf_group_value(CONF_cfg_name, CONF_group_name))
        super().__init__(caption, val, **kwargs)
        urwid.connect_signal(self, 'change', self.callback)

    def callback(self, edit_obj: IntEdit, current_value):
        tmp = current_value or 0
        tmp_int = int(tmp)
        if edit_obj.my_min is not None and tmp_int < edit_obj.my_min:
            edit_obj.set_caption(('header', [f"不能小于{edit_obj.my_min}!", ("white", " "), ]))
        elif edit_obj.my_max is not None and tmp_int > edit_obj.my_max:
            edit_obj.set_caption(('header', [f"不能大于{edit_obj.my_max}!", ("white", " "), ]))
        else:
            edit_obj.set_caption('')
            func.set_conf_group_value(current_value, edit_obj.CONF_cfg_name, edit_obj.CONF_group_name)

    def valid_char(self, ch: str) -> bool:
        """
        Return true for decimal digits.
        """
        return len(ch) == 1 and ch in string.digits

    def keypress(self, size: tuple[int], key: str) -> str | None:
        """
        Handle editing keystrokes.  Remove leading zeros.

        >>> e, size = IntEdit(u"", 5002), (10,)
        >>> e.keypress(size, 'home')
        >>> e.keypress(size, 'delete')
        >>> print(e.edit_text)
        002
        >>> e.keypress(size, 'end')
        >>> print(e.edit_text)
        2
        """
        unhandled = super().keypress(size, key)

        if not unhandled:
            # trim leading zeros
            while self.edit_pos > 0 and self.edit_text[:1] == "0":
                self.set_edit_pos(self.edit_pos - 1)
                self.set_edit_text(self.edit_text[1:])

        return unhandled

    def value(self) -> int:
        """
        Return the numeric value of self.edit_text.

        >>> e, size = IntEdit(), (10,)
        >>> e.keypress(size, '5')
        >>> e.keypress(size, '1')
        >>> e.value() == 51
        True
        """
        if self.edit_text:
            return int(self.edit_text)

        return 0


class PopUpDialog(urwid.WidgetWrap):
    """A dialog that appears with nothing but a close button"""

    signals: typing.ClassVar[list[str]] = ["close"]

    def __init__(self):
        close_button = urwid.Button("that's pretty cool")
        urwid.connect_signal(close_button, "click", lambda button: self._emit("close"))
        pile = urwid.Pile(
            [
                urwid.Text("^^  I'm attached to the widget that opened me. Try resizing the window!\n"),
                close_button,
            ]
        )
        fill = urwid.Filler(pile)
        super().__init__(urwid.AttrMap(fill, "popbg"))


class ThingWithAPopUp(urwid.PopUpLauncher):
    def __init__(self, CONF_cfg_name, CONF_group_name=None, caption="", **kwargs):
        super().__init__(IntEdit(CONF_cfg_name, CONF_group_name=CONF_group_name, caption=caption))

        def xxx(a1, b1):
            self.open_pop_up()

        urwid.connect_signal(self.original_widget, "change", xxx)

    def create_pop_up(self):
        pop_up = PopUpDialog()
        urwid.connect_signal(pop_up, "close", lambda button: self.close_pop_up())
        return pop_up

    def get_pop_up_parameters(self):
        return {"left": 0, "top": 1, "overlay_width": 32, "overlay_height": 7}

    def keypress(self, key: str, size: tuple[int]) -> str | None:
        parsed = super().keypress(key, size)
        if parsed in ("q", "Q"):
            raise urwid.ExitMainLoop("Done")
        return parsed
