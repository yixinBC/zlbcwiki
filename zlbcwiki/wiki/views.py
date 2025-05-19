from diff_match_patch import diff_match_patch
from django import forms
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.core.paginator import Paginator
from django.db import models
from django.forms import ModelForm
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .models import Wiki, WikiImage, WikiPermission, WikiTag, WikiCategory, WikiComment

# Create your views here.


# Wiki创建表单
class WikiForm(ModelForm):
    class Meta:
        model = Wiki
        fields = ["title", "slug", "content", "category", "tags"]
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入Wiki标题'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '输入URL别名'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'rows': 15}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'tags': forms.SelectMultiple(attrs={'class': 'form-select', 'size': '5'}),
        }

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            # Add empty label for category field
            self.fields['category'].empty_label = "请选择分类"
            
            # Check if categories exist, if not, add a warning
            if not WikiCategory.objects.exists():
                self.fields['category'].help_text = "请先创建至少一个分类"
                
            # Check if tags exist, if not, add a warning
            if not WikiTag.objects.exists():
                self.fields['tags'].help_text = "请先创建至少一个标签"


def index(request):
    recent_wikis = Wiki.objects.all().order_by("-updated_at")[:10]  # 获取最近更新的几个Wiki
    categories = WikiCategory.objects.all()  # 获取所有分类
    popular_tags = WikiTag.objects.all()
    stats = {
        "total_wikis": Wiki.objects.count(),
        "total_categories": WikiCategory.objects.count(),
        "total_tags": WikiTag.objects.count(),
    }
    return render(request, "wiki/index.html", {
        "recent_wikis": recent_wikis,
        "categories": categories,
        "popular_tags": popular_tags,
        "stats": stats,
    })


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


def wiki_list(request):
    """显示所有Wiki页面的列表"""
    # 获取所有Wiki页面
    wikis = Wiki.objects.all().order_by("-updated_at")

    # 按类别过滤
    category_slug = request.GET.get("category")
    if category_slug:
        category = get_object_or_404(WikiCategory, slug=category_slug)
        wikis = wikis.filter(category=category)

    # 按标签过滤
    tag_slug = request.GET.get("tag")
    if tag_slug:
        tag = get_object_or_404(WikiTag, slug=tag_slug)
        wikis = wikis.filter(tags=tag)

    # 搜索功能
    query = request.GET.get("q")
    if query:
        wikis = wikis.filter(
            models.Q(title__icontains=query) | models.Q(content__icontains=query)
        )

    # 分页
    paginator = Paginator(wikis, 20)  # 每页显示20条
    page = request.GET.get("page")
    wikis_page = paginator.get_page(page)

    # 获取所有分类和标签用于侧边栏
    categories = WikiCategory.objects.all()
    tags = WikiTag.objects.all()

    return render(
        request,
        "wiki/list.html",
        {
            "wikis": wikis_page,
            "categories": categories,
            "tags": tags,
            "query": query,
            "category_slug": category_slug,
            "tag_slug": tag_slug,
        },
    )


def wiki_detail(request, slug):
    """显示单个Wiki页面详情"""
    # 获取Wiki页面
    wiki = get_object_or_404(Wiki, slug=slug)

    # 权限检查
    has_view_permission = True
    has_edit_permission = False

    if request.user.is_authenticated:
        # 检查用户是否有编辑权限
        has_edit_permission = (
            WikiPermission.objects.filter(
                wiki=wiki, user=request.user, permission__in=["edit", "admin"]
            ).exists()
            or request.user.is_superuser
            or wiki.creator == request.user
        )

    # Markdown渲染
    import markdown

    content_html = markdown.markdown(
        wiki.content,
        extensions=[
            "markdown.extensions.fenced_code",
            "markdown.extensions.tables",
            "markdown.extensions.toc",
        ],
    )

    # 相关Wiki页面
    related_wikis = (
        Wiki.objects.filter(
            models.Q(category=wiki.category) | models.Q(tags__in=wiki.tags.all())
        )
        .exclude(id=wiki.id)
        .distinct()[:5]
    )

    return render(
        request,
        "wiki/detail.html",
        {
            "wiki": wiki,
            "content_html": content_html,
            "has_view_permission": has_view_permission,
            "has_edit_permission": has_edit_permission,
            "related_wikis": related_wikis,
        },
    )


@login_required
def edit_wiki(request, wiki_id):
    wiki = get_object_or_404(Wiki, id=wiki_id)

    if request.method == "POST":
        new_content = request.POST.get("content", "")
        description = request.POST.get("description", "")

        # 保存新版本
        wiki.save_revision(request.user, new_content, description)
        return redirect("wiki_detail", slug=wiki.slug)

    return render(request, "wiki/edit.html", {"wiki": wiki})


@login_required
def upload_wiki_image(request):
    if request.method == "POST" and request.FILES.get("image"):
        wiki_id = request.POST.get("wiki_id")
        wiki = get_object_or_404(Wiki, id=wiki_id)

        # 创建新图片记录
        image = WikiImage(
            title=request.POST.get("title", ""),
            description=request.POST.get("description", ""),
            wiki=wiki,
            uploaded_by=request.user,
            image=request.FILES["image"],
        )
        image.save()

        # 返回成功响应和图片URL
        return JsonResponse(
            {"success": True, "image_url": image.image.url, "title": image.title}
        )

    return JsonResponse({"success": False, "error": "上传失败"})


@login_required
def create_wiki(request):
    """创建新Wiki页面"""
    if request.method == "POST":
        form = WikiForm(request.POST)
        if form.is_valid():
            wiki = form.save(commit=False)
            wiki.creator = request.user
            wiki.save()

            # 保存多对多关系
            form.save_m2m()

            # 创建第一个修订版本
            wiki.save_revision(request.user, wiki.content, "初始创建")

            messages.success(request, "Wiki页面创建成功！")
            return redirect("wiki_detail", slug=wiki.slug)
    else:
        form = WikiForm()

    return render(
        request,
        "wiki/create_edit.html",
        {
            "form": form,
            "is_create": True,
        },
    )


@login_required
def add_comment(request, wiki_id):
    """添加评论"""
    wiki = get_object_or_404(Wiki, id=wiki_id)

    if request.method == "POST":
        content = request.POST.get("content", "").strip()
        if content:
            WikiComment.objects.create(wiki=wiki, user=request.user, content=content)
            messages.success(request, "评论已发布")
        else:
            messages.error(request, "评论内容不能为空")

    return redirect("wiki_detail", slug=wiki.slug)


def view_wiki_history(request, wiki_id):
    wiki = get_object_or_404(Wiki, id=wiki_id)
    revisions_list = wiki.revisions.all().order_by("-created_at")  # type: ignore

    # 设置每页10条记录
    paginator = Paginator(revisions_list, 10)
    page = request.GET.get("page")
    revisions = paginator.get_page(page)

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


def wiki_compare_revisions(request, wiki_id):
    wiki = get_object_or_404(Wiki, id=wiki_id)
    from_revision_id = request.GET.get("from_revision")
    to_revision_id = request.GET.get("to_revision")

    if not from_revision_id or not to_revision_id:
        return redirect("wiki_history", wiki_id=wiki_id)

    # 获取两个版本的内容
    from_content = wiki.get_content_at_revision(from_revision_id)
    to_content = wiki.get_content_at_revision(to_revision_id)

    # 使用 diff-match-patch 生成差异
    dmp = diff_match_patch()
    diff = dmp.diff_main(from_content, to_content)
    dmp.diff_cleanupSemantic(diff)

    # 转换为HTML显示
    html_diff = dmp.diff_prettyHtml(diff)

    from_revision = get_object_or_404(wiki.revisions, id=from_revision_id)  # type: ignore
    to_revision = get_object_or_404(wiki.revisions, id=to_revision_id)  # type: ignore

    return render(
        request,
        "wiki/compare.html",
        {
            "wiki": wiki,
            "from_revision": from_revision,
            "to_revision": to_revision,
            "html_diff": html_diff,
        },
    )
