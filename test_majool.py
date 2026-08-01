import importlib.util
from importlib.machinery import SourceFileLoader
try:
    loader = SourceFileLoader("majool", "majool")
    spec = importlib.util.spec_from_loader("majool", loader)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    print("LOAD_OK has_XuiDB=", hasattr(m, "XuiDB"))
    res = m.XuiDB().make_config(total_gb=1, days=1, limit_ip=1, email="test_patch9", reload=True)
    print("MAKE_OK", bool(res and res[0]), "email=", res[2] if res else None)
except Exception:
    import traceback; traceback.print_exc()
