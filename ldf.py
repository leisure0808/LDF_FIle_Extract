import re


class LINSignal(object):
    def __init__(self):
        self.name = str()
        self.length = None
        self.initialValue = None
        self.publisher = str()
        self.subscriber = list()
        self.responseError = None

    def get_dict_fmt(self):
        return {
            self.name: {
                'length': self.length,
                'initialValue': self.initialValue,
                'publisher': self.publisher,
                'subscriber': self.subscriber,
                'responseError': self.responseError
            }
        }


class LINFrame(object):
    def __init__(self):
        self.name = str()
        self.ID = None
        self.publisher = str()
        self.length = None
        self.signals = list()

    def get_dict_fmt(self):
        return {
            self.name: {
                'frameID': self.ID,
                'publisher': self.publisher,
                'length': self.length,
                'signals': self.signals
            }
        }


class LINNode(object):
    def __init__(self):
        self.name = str()
        self.ID = None
        self.frames = list()

    def get_dict_fmt(self):
        return {
            self.name: {
                'NodeID': self.ID,
                'frames': self.frames,
            }
        }


class ScheduleTable(object):
    def __init__(self):
        self.name = str()
        self.frames = list()

    class Frame:
        def __init__(self, name: str, delay: str):
            self.name = name
            self.delay = delay

        def get_dict_fmt(self):
            return {
                self.name: {
                    'delay': self.delay
                }
            }

    def get_dict_fmt(self):
        return {
            self.name: {
                'frames': self.frames
            }
        }


class LDF(object):
    def __init__(self, file: str):
        self.__file = file
        self.f = None

        self.__protocol_version = re.compile(r'(?<=LIN_protocol_version\s=\s").*(?=")')
        self.__lin_speed = re.compile(r'(?<=LIN_speed\s=\s).*?(?=\skbps)')
        self.__node_attributes = re.compile(r'(?<=Node_attributes\s{)(.|\n)*?}(?=(\n)*?})')
        self.__node = re.compile(r'.*{(?:.|\n)*?}')
        self.__master = re.compile(r'(?<=\n\s\sMaster:).*?(?=;)')
        self.__slaves = re.compile(r'(?<=\n\s\sSlaves:).*?(?=;)')
        self.__frames = re.compile(r'(?<=Frames\s{)(.|\n)*?}(?=(\s|\r|\n)*?})')
        self.__frame = re.compile(r'.*{(?:.|\n)*?}')
        self.__signals = re.compile(r'(?<=Signals\s{)(.|\n)*?(?=(\s|\r|\n)*?})')
        self.__tables = re.compile(r'(?<=Schedule_tables\s{)(.|\n)*?}(?=(\s|\r|\n)*?})')
        self.__table = re.compile(r'.*{(?:.|\n)*?}')
        self.__signal_encoding_types = re.compile(r'(?<=Signal_encoding_types\s{)(.|\n)*?}(?=(\s|\r|\n)*?})')
        self.__signal_encoding_type = re.compile(r'.*{(?:.|\n)*?}')
        self.protocol_version = {'LIN_protocol_version': None}
        self.lin_speed = {'LIN_speed': None}
        self.nodes_attributes = {'Node_attributes': []}
        self.master = {'Master': None}
        self.slaves = {'Slaves': []}
        self.frames = {'Frames': []}
        self.signals = {'Signals': []}
        self.tables = []
        self.signals_encoding = []

        self.phrase()

    def _open_file(self):
        fileHandle = open(self.__file, 'r')
        self.f = fileHandle.read()

    def _basic_info(self):
        # 协议与速率
        self.protocol_version['LIN_protocol_version'] = re.search(self.__protocol_version, self.f).group()
        self.lin_speed['LIN_speed'] = re.search(self.__lin_speed, self.f).group()
        # print(self.protocol_version)
        # print(self.lin_speed)

    def _node_info(self):
        master_info = re.search(self.__master, self.f).group()
        self.master['Master'] = master_info.replace(' ', '').split(',')[0]
        slaves_info = re.search(self.__slaves, self.f).group()
        self.slaves['Slaves'] = slaves_info.replace(' ', '').split(',')
        nodes_attributes_info = re.search(self.__node_attributes, self.f).group()
        nodes = re.findall(self.__node, nodes_attributes_info)
        # print(nodes)
        for node in nodes:
            temp_node = LINNode()
            temp_node.name = re.search(r'.*?(?={)', node).group()
            temp_node.ID = re.search(r'(?<=configured_NAD\s=\s).*?(?=\s;)', node)
            node_without_name = re.search(r'(?<={)(?:.|\n)*?}', node).group()
            config_frames = re.search(r'(?<=configurable_frames\s{)(?:.|\n)*?(?=(\s|\n)*?})', node_without_name).group()
            temp_node.frames = config_frames.replace('\n', '').replace(' ', '').split(';')[:-1]
            self.nodes_attributes['Node_attributes'].append(temp_node.get_dict_fmt())

    def _frame_info(self):
        frames_str = re.search(self.__frames, self.f).group()
        frames = re.findall(self.__frame, frames_str)

        for frame in frames:
            temp_frame = LINFrame()
            temp_frame.name = re.search(r'.*?(?=:)', frame).group()
            temp_frame.ID = re.search('(?<=' + temp_frame.name + ':)' + '\s*\d+?(?=,)', frame).group()
            temp_frame.publisher = re.search('(?<=' + temp_frame.ID + ',\s).*?(?=,)', frame).group()
            temp_frame.length = re.search('(?<=' + temp_frame.publisher + ',\s).*?(?={)', frame).group()
            signals = re.search('(?<={)(?:.|\n)*?(?=})', frame).group()
            for signal in signals.replace('\n', '').replace(' ', '').split(';'):
                if signal:
                    temp_signal = signal.split(',')
                    temp_frame.signals.append({temp_signal[0]: {'startbit': temp_signal[1]}})
            self.frames['Frames'].append(temp_frame.get_dict_fmt())

    def _signal_info(self):
        signals_str = re.search(self.__signals, self.f).group()
        for signal in signals_str.replace('\n', '').replace(' ', '').split(';'):
            if signal:
                temp_signal = LINSignal()
                temp_info = signal.split(',')
                temp_signal.name = temp_info[0].split(':')[0]
                temp_signal.length = temp_info[0].split(':')[1]
                temp_signal.initialValue = temp_info[1]
                temp_signal.publisher = temp_info[2]
                temp_signal.subscriber = [temp_info[i] for i in range(3, len(temp_info))]
                self.signals['Signals'].append(temp_signal.get_dict_fmt())

    def _table_info(self):
        tables_str = re.search(self.__tables, self.f).group()
        # print(tables_str)
        tables = re.findall(self.__table, tables_str)
        # print(tables)
        for table in tables:
            temp_table = ScheduleTable()
            temp_table.name = re.search(r'.*?(?={)', table).group()
            frames = re.search(r'(?<={)(?:.|\n)*?(?=})', table).group().replace('\n', '').split(';')
            for frame in frames:
                frame = frame.strip()
                if frame:
                    temp_info = frame.split(' ')
                    temp_table.frames.append(temp_table.Frame(temp_info[0], temp_info[2]).get_dict_fmt())
            self.tables.append(temp_table.get_dict_fmt())

    def _signal_type_info(self):
        encoding_types_str = re.search(self.__signal_encoding_types, self.f).group()
        print(encoding_types_str)
        encoding_type = re.findall(self.__signal_encoding_type, encoding_types_str)
        print(encoding_type)
        for signal in encoding_type:
            name = re.search(r'.*?(?={)', signal).group().replace(' ', '')
            signal_types = re.search(r'(?<={)(?:.|\n)*?(?=})', signal).group().replace('\n', '').replace(' ', '').split(';')
            print(name, '\n', signal_types)
            signal_value_list = list()
            for value in signal_types:
                if value:
                    value = value.split(',')
                    print(value)
                    signal_value_list.append({value[1]: value[2]})
            self.signals_encoding.append({name: signal_value_list})

    def phrase(self):
        self._open_file()

        self._basic_info()
        self._node_info()
        self._frame_info()
        self._signal_info()
        self._table_info()
        self._signal_type_info()

        print(self.signals_encoding)


if __name__ == '__main__':
    LDF("RoofUnit.ldf")
