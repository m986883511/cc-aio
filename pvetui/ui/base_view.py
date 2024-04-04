import subprocess
import logging
import time
import datetime

import urwid

from pvetui import ui
from pvetui.config import CONF, AIO_CONF_PATH
from cg_utils import func, execute, AUTHOR_NAME

LOG = logging.getLogger(__name__)


class KollaBaseConfig:
    def __init__(self):
        self.kolla_rc_path = f'/etc/{AUTHOR_NAME}/admin-openrc.sh'
        self.ansible_hosts = f'/etc/{AUTHOR_NAME}/hosts'


class BaseConfigView(KollaBaseConfig):
    def __init__(self, button):
        super(BaseConfigView, self).__init__()
        CONF.reload_config_files()
        self.origin_layout_button: urwid.Button = button
        self.origin_layout_button_label = button.label
        self.pile_view = urwid.Pile([urwid.Divider()])
        self.note_text = urwid.Text('', align='left')
        self._note_msg = ''
        self._note_alarm = None
        self._note_flag_count = 0
        self._note_alarm_time = 5

    @property
    def note_msg(self):
        return self._note_msg

    @note_msg.setter
    def note_msg(self, msg):
        self._note_msg = msg
        LOG.error(msg)
        if self._note_alarm:
            self._stop_note_alarm()
        self._start_note_alarm()

    def _start_note_alarm(self, loop=None, user_data=None):
        self._note_alarm = ui.top_loop.set_alarm_in(self._note_alarm_time, self._start_note_alarm)
        self._note_flag_count += 1
        if self._note_flag_count == 1:
            self.note_text.set_text(self.note_msg)
        else:
            self.note_text.set_text('')
            self._stop_note_alarm()
    
    def _stop_note_alarm(self):
        self._note_flag_count = 0
        if self._note_alarm:
            ui.top_loop.remove_alarm(self._note_alarm)
        self._note_alarm = None

    def update_view(self):
        raise NotImplementedError

    def show(self):
        raise NotImplementedError
    
    def save_CONF_group_keys(self, group, keys):
        for key in keys:
            value = getattr(getattr(CONF, group), key)
            LOG.info(f'crudini save group={group} key={key} value={value}')
            flag, content = execute.use_crudini_save_CONF_to_path(AIO_CONF_PATH, group, key)
            assert flag==0, f'update group={group} key={key} value={value} to {AIO_CONF_PATH} failed, err={content}'
        self.rsync_to_other_control_nodes()

    def rsync_to_other_control_nodes(self):
        if not CONF.openstack.rsync_config_to_other_control_nodes:
            return
        cmd = f'crudini --get {AIO_CONF_PATH} openstack control_nodes'
        flag, content = execute.execute_command(cmd)
        if flag != 0:
            LOG.warning(f'rsync_to_other_control_nodes read control_nodes failed, err={content}, skip rsync!')
            return
        control_nodes = func.get_string_split_list(content, split_flag=',')
        current_hostname = func.get_current_node_hostname()
        other_control_nodes = [x for x in control_nodes if x != current_hostname ]
        for node in other_control_nodes:
            flag, content = execute.execute_command(f'cg-hostcli ssh rsync-dir-to-remote-host {node} /etc/cg', shell=False, timeout=5)
            if flag == 0:
                LOG.info(f'rsync_to_other_control_nodes to {node} success')
            else:
                LOG.error(f'rsync_to_other_control_nodes to {node} failed, err={content}')


class BaseConsoleView:
    def __init__(self, origin_view: BaseConfigView, result_button_text="强行结束", console_line_number=CONF.console_max_item_number):
        self.alarm = None
        self.proc = None
        self.origin_view = origin_view
        self.success_text = '执行成功 点击此按钮返回上一层'
        self.failed_text = '执行失败 点击此按钮返回上一层'
        self.output_widget = urwid.Text("")
        self.result_button = urwid.Button(result_button_text, self.result_button_click, align='center')
        self.console_list = func.FixedSizeList(console_line_number)
        self.need_run_cmd_list = []
        self.current_cmd_index = 0
        self._task_start_time = None
        self._task_end_time = None

    def result_button_click(self, button):
        if hasattr(self.origin_view, 'update_view'):
            self.origin_view.update_view()
        return ui.return_last(button)
    
    def update_result_button(self):
        if not self._task_start_time:
            return
        use_time = int(time.perf_counter() - self._task_start_time)
        temp = f'正在执行 请勿中断 已用时{use_time}秒'
        self.result_button.set_label(temp)

    def start_alarm(self, loop=None, user_data=None):
        self.alarm = ui.top_loop.set_alarm_in(1, self.start_alarm)
        self.update_result_button()
        if self.proc is None:
            LOG.info(f'run first cmd, cmd_index={self.current_cmd_index}')
            self._task_start_time = time.perf_counter()
            self.run_cmd()
            return
        return_code = self.proc.poll()
        if return_code is not None:
            if return_code==0:
                cmd = self.get_cmd(run_complete=True)
                if cmd:
                    LOG.info(f'run next cmd, cmd_index={self.current_cmd_index}')
                    self.run_cmd()
                    return
                else:
                    self.result_button.set_label(self.success_text)
                    self.stop_alarm()
                    self.task_success_callback()
            else:
                self.result_button.set_label(self.failed_text)
                self.stop_alarm()
                self.task_failed_callback()

    def task_success_callback(self):
        pass

    def task_failed_callback(self):
        pass

    def stop_alarm(self):
        self._task_end_time = time.perf_counter()
        use_time = int(self._task_end_time - self._task_start_time)
        end_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        time_string = f'\n{CONF.tui_title} run end, end at {end_time}, use {use_time} seconds\n'
        self.received_output(time_string)
        if self.alarm:
            ui.top_loop.remove_alarm(self.alarm)
        self.alarm = None

    def received_output(self, data):
        data = data.decode("utf8") if isinstance(data, bytes) else data
        self.console_list.append(data)
        self.output_widget.set_text(str(self.console_list))

    def get_cmd(self, run_complete=False):
        cmd = ''
        if run_complete:
            if self.current_cmd_index+1<len(self.need_run_cmd_list):
                self.current_cmd_index+=1
                cmd = self.need_run_cmd_list[self.current_cmd_index]
        else:
            if self.current_cmd_index<len(self.need_run_cmd_list):
                cmd = self.need_run_cmd_list[self.current_cmd_index]
        if cmd:
            LOG.info(f'now run cmd={cmd}')
            return cmd

    def run_cmd(self):
        write_fd = ui.top_loop.watch_pipe(self.received_output)
        cmd = self.get_cmd()
        if not cmd:
            err_msg = f'get cmd failed, index={self.current_cmd_index}, cmd_list={self.need_run_cmd_list}'
            raise Exception(cmd)
        self.received_output(f'\nNow {CONF.tui_title} Run: {cmd}\n')
        self.proc = subprocess.Popen(cmd, stdout=write_fd, close_fds=True, shell=True)

    def show(self):
        raise NotImplementedError
