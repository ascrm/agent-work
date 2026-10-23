# W1 Lab：Python 差异练习场

这里是一次性实验区，随便写、随便删。规则只有一条：

> **验证完一个想法，把结论写进 `notes/w01.md`，然后就可以扔掉这个文件。**

建议实验：

1. `async_demo.py` —— 对比 `time.sleep(3)` 和 `asyncio.sleep(3)` 在并发下的区别
2. `pydantic_demo.py` —— 对比默认校验、`Field` 约束、`model_validate` 的行为
3. `depends_demo.py` —— 手写一个最小 `Depends` 例子，理解它不是容器

运行：`python async_demo.py`（不需要装依赖的实验直接用系统 Python 即可）
