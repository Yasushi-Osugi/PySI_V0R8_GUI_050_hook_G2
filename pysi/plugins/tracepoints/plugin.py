# pysi/plugins/tracepoints/plugin.py
def register(bus):
    def log_filter(value=None, **ctx):
        lg = ctx.get("logger")
        name = ctx.get("_hook_name")
        if lg: lg.info("[trace] filter fired: %s", name)
        return value

    def log_action(**ctx):
        lg = ctx.get("logger")
        name = ctx.get("_hook_name")
        if lg: lg.info("[trace] action fired: %s", name)

    # 代表的なイベントを広めに“盗聴”
    for name in [
        "timebase:calendar:build",
        "scenario:preload",
        "plan:graph:build",
        "plan:post_build",
        "plan:psi:init",
        "plan:allocation:s_to_p_push",
        "ui:psi:show",
    ]:
        bus.add_filter(name, lambda v=None, _n=name, **c: log_filter(v, _hook_name=_n, **c), priority=99)
        bus.add_action(name, lambda _n=name, **c: log_action(_hook_name=_n, **c), priority=99)
