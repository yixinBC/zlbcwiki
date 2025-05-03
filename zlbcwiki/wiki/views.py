from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from .models import Wiki
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


@login_required
def edit_wiki(request, wiki_id):
    wiki = get_object_or_404(Wiki, id=wiki_id)

    if request.method == "POST":
        new_content = request.POST.get("content", "")
        description = request.POST.get("description", "")

        # 保存新版本
        wiki.save_revision(request.user, new_content, description)
        return redirect("wiki_detail", wiki_id=wiki.id)

    return render(request, "wiki/edit.html", {"wiki": wiki})


def view_wiki_history(request, wiki_id):
    wiki = get_object_or_404(Wiki, id=wiki_id)
    revisions = wiki.revisions.all().order_by("-created_at")  # type: ignore

    return render(request, "wiki/history.html", {"wiki": wiki, "revisions": revisions})


def view_wiki_revision(request, wiki_id, revision_id):
    wiki = get_object_or_404(Wiki, id=wiki_id)
    revision = get_object_or_404(wiki.revisions, id=revision_id)  # type: ignore

    # 获取该修订版本的内容
    content = wiki.get_content_at_revision(revision_id)

    return render(
        request,
        "wiki/revision.html",
        {"wiki": wiki, "revision": revision, "content": content},
    )
