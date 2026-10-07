from django.db import models


class Analysis(models.Model):
    comment = models.TextField()
    platform = models.CharField(max_length=20, default="custom")
    user_id = models.CharField(max_length=100, blank=True, default="")
    comment_id = models.CharField(max_length=100, blank=True, default="")
    categories = models.CharField(max_length=200)
    severity = models.CharField(max_length=10)
    needs_review = models.BooleanField(default=False)
    confidence = models.FloatField(default=0)
    scores = models.JSONField(default=dict)
    action = models.CharField(max_length=10, default="ALLOW")
    escalate = models.BooleanField(default=False)
    report_required = models.BooleanField(default=False)
    restrict_user = models.BooleanField(default=False)
    strikes = models.IntegerField(default=0)
    # incident workflow: none -> open -> confirmed / dismissed
    status = models.CharField(max_length=10, default="none")
    reviewed_by = models.CharField(max_length=100, blank=True, default="")
    reviewed_at = models.DateTimeField(null=True, blank=True)
    # source details (filled for YouTube comments fetched after this update)
    video_id = models.CharField(max_length=20, blank=True, default="")
    author_channel_id = models.CharField(max_length=100, blank=True, default="")
    posted_at = models.CharField(max_length=40, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.action} | {self.severity} | {self.comment[:40]}"


class Post(models.Model):
    author = models.CharField(max_length=100)
    caption = models.TextField()
    color = models.CharField(max_length=20, default="#0E9F8E")
    likes = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]


class Comment(models.Model):
    # state: published (visible) / held (waiting for a moderator) / removed
    post = models.ForeignKey(Post, related_name="comments", on_delete=models.CASCADE)
    user_id = models.CharField(max_length=100)
    text = models.TextField()
    state = models.CharField(max_length=10, default="published")
    analysis = models.OneToOneField(Analysis, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="feed_comment")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class CommentReport(models.Model):
    comment = models.ForeignKey(Comment, related_name="reports", on_delete=models.CASCADE)
    reporter = models.CharField(max_length=100)
    reason = models.CharField(max_length=100, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("comment", "reporter")
