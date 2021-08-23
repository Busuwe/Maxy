from __future__ import annotations

from typing import Optional

import serial


def escape_message(msg):
    result = bytearray()
    for c in msg:
        if c >= 0xfc:
            result.append(0xfc)
        result.append(c)
    return result


def range_validate_int(val, minimum, maximum, param_name):
    if not isinstance(val, int):
        raise ValueError(f"Parameter '{param_name}' must be an int, received {type(val)}")
    if minimum <= val <= maximum:
        return val
    raise ValueError(f"Parameter '{param_name}' is outside the allowed range. Got '{val}', expected it to be {minimum}-{maximum}")


class MaxyMessages:

    MID_RESET_CONFIG = b"\x32"
    MID_SET_ALL_INTENSITY = b"\x33"
    MID_SET_MODULE_TYPE = b"\x3a"
    MID_ENABLE_MODULE = b"\x3b"

    MID_SET_MODULE_TARGET = b"\x42"
    MID_SET_SUB_MODULE_TARGET = b"\x43"
    MID_SET_MODULE_IMMEDIATE_TARGET = b"\x44"
    MID_SET_SUB_MODULE_IMMEDIATE_TARGET = b"\x45"

    MID_SET_MODULE_INTENSITY = b"\x46"
    MID_SET_MODULE_SPEED_DIVIDER = b"\x47"

    @classmethod
    def reset_all_module_config_message(cls):
        return cls.MID_RESET_CONFIG

    @classmethod
    def set_all_module_intensity(cls, intensity):
        range_validate_int(intensity, 0, 15, "intensity")
        intensity_raw = intensity.to_bytes(length=1, byteorder="big", signed=False)
        return cls.MID_SET_ALL_INTENSITY + intensity_raw

    @classmethod
    def set_module_target_message(cls, module_index, target):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(target, -9999999, 99999999, "target")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        target_raw = target.to_bytes(length=4, byteorder="big", signed=True)
        return cls.MID_SET_MODULE_TARGET + module_raw + target_raw

    @classmethod
    def set_module_immediate_target_message(cls, module_index,  target):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(target, -9999999, 99999999, "target")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        target_raw = target.to_bytes(length=4, byteorder="big", signed=True)
        return cls.MID_SET_MODULE_IMMEDIATE_TARGET + module_raw + target_raw

    @classmethod
    def set_sub_module_immediate_target_message(cls, module_index, sub_module, target):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(target, -9999999, 99999999, "target")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        sub_module_raw = sub_module.to_bytes(length=1, byteorder="big", signed=False)
        target_raw = target.to_bytes(length=4, byteorder="big", signed=True)
        return cls.MID_SET_SUB_MODULE_IMMEDIATE_TARGET + module_raw + sub_module_raw + target_raw

    @classmethod
    def set_sub_module_target_message(cls, module_index, sub_module, target):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(sub_module, 0, 7, "sub_module")
        range_validate_int(target, -9999999, 99999999, "target")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        sub_module_raw = sub_module.to_bytes(length=1, byteorder="big", signed=False)
        target_raw = target.to_bytes(length=4, byteorder="big", signed=True)
        return cls.MID_SET_SUB_MODULE_TARGET + module_raw + sub_module_raw + target_raw

    @classmethod
    def set_module_intensity(cls, module_index, intensity):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(module_index, 0, 15, "intensity")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        intensity_raw = intensity.to_bytes(length=1, byteorder="big", signed=False)
        return cls.MID_SET_MODULE_INTENSITY + module_raw + intensity_raw

    @classmethod
    def set_module_speed_divider(cls, module_index, intensity):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(module_index, 0, 65000, "speed_divider")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        speed_divider_raw = intensity.to_bytes(length=2, byteorder="big", signed=False)
        return cls.MID_SET_MODULE_INTENSITY + module_raw + speed_divider_raw
    
    @classmethod
    def set_module_type(cls, module_index, module_type):
        range_validate_int(module_index, 0, 63, "module_index")
        range_validate_int(module_type, 0, 63, "module_type")
        module_raw = module_index.to_bytes(length=1, byteorder="big", signed=False)
        module_type_raw = module_type.to_bytes(length=1, byteorder="big", signed=False)
        return cls.MID_SET_MODULE_TYPE + module_raw + module_type_raw


class DictObject(object):
    def __init__(self, **kwargs):
        self.values = kwargs
        
    def clear(self):
        self.values = {}

    def __getitem__(self, item):
        if item in self.values:
            return self.values[item]
        raise KeyError(item)
    
    def __setitem__(self, key, value):
        self.values[key] = value

    def __getattr__(self, item):
        if item in self.values:
            return self.values[item]
        raise AttributeError(item)

    def __contains__(self, item):
        return item in self.values

    def get(self, item, default=None):
        try:
            return self[item]
        except KeyError:
            return default

    def __repr__(self):
        return str(self)

    def __iter__(self):
        return iter(self.values)

    def __str__(self):
        value_list = []
        for k in self.values:
            v = self.values[k]
            value_list.append(str(k) + "=" + str(v))
        return "{" + ", ".join(value_list) + "}"
    
class MaxyController:

    def __init__(self):
        self._serial: Optional[serial.Serial] = None
        self.index: list[MaxyModule] = []
        self.name: DictObject[str, MaxyModule] = DictObject()

    def define_modules(self, module_definitions: list[MaxModuleDef]):
        self.index.clear()
        self.name.clear()
        
        for index, module_def in enumerate(module_definitions):
            if not module_def:
                continue
            new_module = module_def.module_type(self, index)
            self.index.append(new_module)
            if module_def.name:
                self.name[module_def.name] = new_module
            if module_def.module_type.SUB_MODULE_COUNT > 1 and module_def.sub_module_names:
                for name, sub_module_index in zip(module_def.sub_module_names,
                                                  range(module_def.module_type.SUB_MODULE_COUNT)):
                    if name:
                        self.name[name] = new_module.sub_modules[sub_module_index]

    def connect(self, port: str, baudrate: int = 9600, timeout: float = 5):
        self._serial = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        self.configure_module_types()

    def configure_module_types(self):
        for module in self.index:
            self.send_message(
                MaxyMessages.set_module_type(module.module_index, module.MODULE_TYPE_ID)
            )
            
    def set_global_intensity(self, intensity):
        self.send_message(MaxyMessages.set_all_module_intensity(intensity))
            
    @property
    def serial(self):
        if self._serial and self._serial.isOpen():
            return self._serial
        else:
            raise IOError("The serial connection is closed")

    def send_message(self, msg):
        self.serial.write(b"\xfd" + escape_message(msg) + b"\xfe")


def clamp(value, min_value, max_value):
    return min(max_value, max(min_value, value))


class MaxyModule:

    SUB_MODULE_COUNT = 1
    TARGET_MIN = -9999999
    TARGET_MAX = 99999999
    MODULE_TYPE_ID = 0
    ALLOW_MAIN_MODULE_TARGET_CHANGES = True
    
    def __init__(self, controller: MaxyController, module_index: int) -> None:
        self.controller = controller
        self.module_index = module_index
        self._intensity: int = 0
        self.sub_modules: list[MaxySubModule] = [MaxySubModule(self, i) for i in range(self.SUB_MODULE_COUNT)]
    
    def _get_intensity(self):
        return self._intensity
    
    def _set_intensity(self, intensity):
        intensity = clamp(intensity, 0, 15)
        if intensity != self._intensity:
            self._intensity = intensity
            self.controller.send_message(MaxyMessages.set_module_intensity(self.module_index, intensity))

    intensity = property(_get_intensity, _set_intensity)
    
    def _set_target(self, target):
        if not self.ALLOW_MAIN_MODULE_TARGET_CHANGES:
            raise TypeError("You can't change the target directly on this module. Change it on submodules instead")
        self.sub_modules[0].target = target
        target = clamp(target, self.TARGET_MIN, self.TARGET_MAX)

    def _get_target(self):
        return self.sub_modules[0].target
    
    target = property(_get_target, _set_target)
    
    def set_immediate_target(self, target):
        if not self.ALLOW_MAIN_MODULE_TARGET_CHANGES:
            raise TypeError("You can't change the target directly on this module. Change it on submodules instead")
        self.sub_modules[0].set_immediate_target(target)

    immediate_target = property(fset=set_immediate_target)
    

class MaxyModule_8x7seg(MaxyModule):
    
    SUB_MODULE_COUNT = 1
    TARGET_MIN = -9999999
    TARGET_MAX = 99999999
    MODULE_TYPE_ID = 3
    

class MaxyModule_2x4x7seg(MaxyModule):
    
    SUB_MODULE_COUNT = 2
    TARGET_MIN = -999
    TARGET_MAX = 9999
    ALLOW_MAIN_MODULE_TARGET_CHANGES = False
    MODULE_TYPE_ID = 4
    
class MaxySubModule:
    
    def __init__(self, module, sub_module_id):
        self.module = module
        self.sub_module_id = sub_module_id
        self._target = 0
        
    def _set_target(self, target):
        target = clamp(target, self.module.TARGET_MIN, self.module.TARGET_MAX)
        if target != self._target:
            self._target = target
            self.module.controller.send_message(
                MaxyMessages.set_sub_module_target_message(
                    self.module.module_index,
                    self.sub_module_id,
                    target,
                ))
    
    def _get_target(self):
        return self._target
    
    target = property(_get_target, _set_target)
    
    def set_immediate_target(self, target):
        target = clamp(target, self.module.TARGET_MIN, self.module.TARGET_MAX)
        if target != self._target:
            self._target = target
            self.module.controller.send_message(
                MaxyMessages.set_sub_module_immediate_target_message(
                    self.module.module_index,
                    self.sub_module_id,
                    target,
                ))
    
    immediate_target = property(fset=set_immediate_target)


class MaxModuleDef:

    def __init__(self, name, module_type, sub_modules=None):
        self.name = name
        self.module_type = module_type
        self.sub_module_names = sub_modules
