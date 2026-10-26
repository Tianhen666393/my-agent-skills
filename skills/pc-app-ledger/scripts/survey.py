import winreg
import os
import sys
import json

def get_installed_apps():
    roots = [
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
        (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
    ]
    apps = []
    seen = set()
    
    ignore_keywords = [
        "security update", "update for", "hotfix", "redistributable",
        ".net framework", ".net desktop runtime", ".net host", "windows sdk",
        "language pack", "kb4", "kb5", "microsoft visual c++", "edge update"
    ]
    
    for hkey, subkey in roots:
        try:
            key = winreg.OpenKey(hkey, subkey)
        except OSError:
            continue
        num_subkeys = winreg.QueryInfoKey(key)[0]
        for i in range(num_subkeys):
            try:
                sub_name = winreg.EnumKey(key, i)
                sub_key = winreg.OpenKey(key, sub_name)
            except OSError:
                continue
            try:
                display_name, _ = winreg.QueryValueEx(sub_key, "DisplayName")
            except OSError:
                winreg.CloseKey(sub_key)
                continue
            if not display_name or not display_name.strip():
                winreg.CloseKey(sub_key)
                continue
            name = display_name.strip()
            name_lower = name.lower()
            if any(k in name_lower for k in ignore_keywords):
                winreg.CloseKey(sub_key)
                continue
            try:
                is_sys, _ = winreg.QueryValueEx(sub_key, "SystemComponent")
                if is_sys == 1:
                    winreg.CloseKey(sub_key)
                    continue
            except OSError:
                pass
            version = ""
            try:
                version, _ = winreg.QueryValueEx(sub_key, "DisplayVersion")
            except OSError:
                pass
            install_loc = ""
            try:
                install_loc, _ = winreg.QueryValueEx(sub_key, "InstallLocation")
            except OSError:
                pass
            icon = ""
            try:
                icon, _ = winreg.QueryValueEx(sub_key, "DisplayIcon")
            except OSError:
                pass
            winreg.CloseKey(sub_key)
            if name_lower in seen:
                continue
            seen.add(name_lower)
            
            best_path = install_loc
            if not best_path and icon:
                clean_icon = icon.split(',')[0].strip('\"\'')
                if os.path.exists(clean_icon):
                    best_path = clean_icon
            
            # Simple category inference
            category = "常用应用与工具"
            if any(w in name_lower for w in ['altium', 'quartus', 'vivado', 'keil', 'ads', 'multisim', 'eesof', 'filter42']):
                category = "专业EDA与电子设计"
            elif any(w in name_lower for w in ['git', 'python', 'node', 'code', 'ide', 'studio', 'github']):
                category = "开发与编程环境"
            elif any(w in name_lower for w in ['armoury', 'hub', 'driver', 'asus', 'geforce', 'intel', 'amd']):
                category = "硬件与外设驱动"
            elif any(w in name_lower for w in ['bandizip', '7-zip', 'clash', 'pot', 'everything', 'snipaste']):
                category = "系统与效率工具"
            elif any(w in name_lower for w in ['office', 'word', 'excel', 'onenote', 'wechat', 'qq', 'netdisk']):
                category = "日常办公与通讯"
            elif any(w in name_lower for w in ['game', 'mihoyo', 'steam', 'bettergi', '崩坏', '原神', '绝区零']):
                category = "游戏与娱乐"

            apps.append({
                "name": name,
                "category": category,
                "version": str(version).strip() or "未提供",
                "path": str(best_path).strip(),
                "notes": ""
            })
        winreg.CloseKey(key)
    return apps

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    candidates = get_installed_apps()
    print(json.dumps(candidates, ensure_ascii=False, indent=2))
