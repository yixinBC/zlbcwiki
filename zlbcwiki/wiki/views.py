from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import login
# Create your views here.


def index(request):
    return HttpResponse("Hello, world. You're at the wiki index.")


def register(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()  # 保存新用户
            login(request, user)  # 注册后自动登录 (可选)
            messages.success(request, "注册成功！")
            # 重定向到首页或其他页面
            return redirect("index")  # 确保你有一个名为 'index' 的 URL
        else:
            # 表单无效，重新显示表单及错误信息
            messages.error(request, "注册失败，请检查输入信息。")
    else:
        # GET 请求，显示空的注册表单
        form = UserCreationForm()
    # 渲染注册页面模板
    return render(request, "registration/register.html", {"form": form})
