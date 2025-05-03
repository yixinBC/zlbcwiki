from django.db import models
from django.conf import settings
from diff_match_patch import diff_match_patch


class Wiki(models.Model):
    """存储Wiki页面的内容，关联到修订历史"""

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=200)
    content = models.TextField()
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
