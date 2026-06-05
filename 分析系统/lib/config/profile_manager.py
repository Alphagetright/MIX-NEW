# -*- coding: utf-8 -*-
"""配置集管理 —— 多环境配置切换"""

import os
import json


class ProfileManager:
    """配置集管理器"""

    def __init__(self, profiles_dir=None, active_profile="default"):
        self.profiles_dir = profiles_dir
        self.active_profile = active_profile
        self._profiles = {}
        self._loaded = False

    def set_profiles_dir(self, profiles_dir):
        self.profiles_dir = profiles_dir
        self._loaded = False

    def _ensure_loaded(self):
        if self._loaded or not self.profiles_dir:
            return
        if not os.path.exists(self.profiles_dir):
            os.makedirs(self.profiles_dir, exist_ok=True)
            return
        for fname in os.listdir(self.profiles_dir):
            if fname.endswith(".json"):
                name = fname[:-5]
                fpath = os.path.join(self.profiles_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        self._profiles[name] = json.load(f)
                except Exception:
                    self._profiles[name] = {}
        self._loaded = True

    def list_profiles(self):
        self._ensure_loaded()
        return list(self._profiles.keys())

    def get_profile(self, name=None):
        self._ensure_loaded()
        return self._profiles.get(name or self.active_profile, {})

    def set_active(self, name):
        self._ensure_loaded()
        if name in self._profiles:
            self.active_profile = name
            return True
        return False

    def save_profile(self, name, data):
        self._ensure_loaded()
        self._profiles[name] = data
        if self.profiles_dir:
            os.makedirs(self.profiles_dir, exist_ok=True)
            fpath = os.path.join(self.profiles_dir, f"{name}.json")
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

    def delete_profile(self, name):
        self._ensure_loaded()
        if name in self._profiles:
            del self._profiles[name]
            if self.profiles_dir:
                fpath = os.path.join(self.profiles_dir, f"{name}.json")
                if os.path.exists(fpath):
                    os.remove(fpath)
            return True
        return False

    def merge_profile(self, name, data):
        current = self.get_profile(name)
        self._deep_merge(current, data)
        self.save_profile(name, current)
        return current

    def _deep_merge(self, base, override):
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._deep_merge(base[key], value)
            else:
                base[key] = value

    def switch_to(self, name):
        if self.set_active(name):
            return self.get_profile()
        return None
