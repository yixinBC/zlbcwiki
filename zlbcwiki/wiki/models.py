from django.db import models
from django.conf import settings
from diff_match_patch import diff_match_patch


class WikiCategory(models.Model):
    """Wiki 页面分类"""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    parent = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="children",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Wiki 分类"


class WikiTag(models.Model):
    """Wiki 页面标签"""

    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(max_length=50, unique=True)

    def __str__(self):
        return self.name


class Wiki(models.Model):
    """存储Wiki页面的内容，关联到修订历史"""

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, help_text="URL友好的标识符")
    content = models.TextField()
    category = models.ForeignKey(
        WikiCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wikis",
    )
    tags = models.ManyToManyField(WikiTag, blank=True, related_name="wikis")
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_wikis",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save_revision(self, user, new_content, description=""):
        """保存新版本并创建修改记录"""
        dmp = diff_match_patch()
        # 创建从当前内容到新内容的补丁
        patches = dmp.patch_make(self.content, new_content)
        patch_text = dmp.patch_toText(patches)

        # 创建修改记录
        revision = WikiRevision.objects.create(
            wiki=self, user=user, patch=patch_text, description=description
        )

        # 更新内容
        self.content = new_content
        self.save()

        return revision

    def get_content_at_revision(self, revision_id):
        """获取指定修订版本的内容"""
        # 获取所有修订，直到指定的修订
        revisions = self.revisions.filter(id__lte=revision_id).order_by("created_at")  # type: ignore

        # 从初始内容开始，逐个应用补丁
        content = self.content
        dmp = diff_match_patch()

        # 对每个修订应用补丁
        for rev in revisions:
            patches = dmp.patch_fromText(rev.patch)
            content, _ = dmp.patch_apply(patches, content)

        return content

    def get_absolute_url(self):
        from django.urls import reverse

        return reverse("wiki:detail", kwargs={"slug": self.slug})

    class Meta:
        ordering = ["-updated_at"]


class WikiRevision(models.Model):
    """存储Wiki页面的修订历史"""

    id = models.AutoField(primary_key=True)
    wiki = models.ForeignKey(Wiki, on_delete=models.CASCADE, related_name="revisions")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="wiki_revisions",
    )
    patch = models.TextField()  # 存储文本差异的补丁
    description = models.TextField(blank=True)  # 修改说明
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"修订 {self.id} - {self.wiki.title} ({self.created_at})"


class WikiImage(models.Model):
    """Wiki 页面使用的图片"""

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200, help_text="图片标题")
    image = models.ImageField(upload_to="wiki_images/%Y/%m/")
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="uploaded_images",
    )
    wiki = models.ForeignKey(
        Wiki,
        on_delete=models.CASCADE,
        related_name="images",
        null=True,
        blank=True,
        help_text="关联的Wiki页面，可以为空表示未使用的图片",
    )
    description = models.TextField(blank=True, help_text="图片描述")
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ["-uploaded_at"]


class WikiPermission(models.Model):
    """Wiki 页面访问权限控制"""

    PERMISSION_CHOICES = (
        ("view", "查看"),
        ("edit", "编辑"),
        ("admin", "管理"),
    )

    wiki = models.ForeignKey(Wiki, on_delete=models.CASCADE, related_name="permissions")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    permission = models.CharField(max_length=10, choices=PERMISSION_CHOICES)

    class Meta:
        unique_together = ("wiki", "user", "permission")
        verbose_name_plural = "Wiki 权限"


class WikiComment(models.Model):
    """Wiki 页面评论"""

    wiki = models.ForeignKey(Wiki, on_delete=models.CASCADE, related_name="comments")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="wiki_comments",
    )
    content = models.TextField()
    parent = models.ForeignKey(
        "self", on_delete=models.CASCADE, null=True, blank=True, related_name="replies"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
