from django.test import TestCase
from django.urls import reverse

from accounts.models import Follow, User

from .models import Like, Post

PASSWORD = "strong-pass-123"


def make_user(name, verified=True):
    user = User.objects.create_user(name, f"{name}@example.com", PASSWORD)
    user.email_verified = verified
    user.save()
    return user


class PostFlowTests(TestCase):
    def setUp(self):
        self.alice = make_user("alice")
        self.bob = make_user("bob")
        self.client.force_login(self.alice)

    def test_compose_requires_verified_email(self):
        self.client.force_login(make_user("carol", verified=False))
        response = self.client.post(reverse("compose"), {"content": "hi"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Post.objects.count(), 0)

    def test_compose_creates_post(self):
        response = self.client.post(reverse("compose"), {"content": "hello world"})
        self.assertRedirects(response, reverse("home"))
        self.assertEqual(Post.objects.get().content, "hello world")

    def test_compose_via_htmx_returns_card(self):
        response = self.client.post(reverse("compose"), {"content": "htmx post"}, headers={"HX-Request": "true"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "htmx post")

    def test_home_feed_only_shows_followed_users(self):
        Post.objects.create(author=self.bob, content="post from bob")
        self.assertNotContains(self.client.get(reverse("home")), "post from bob")
        Follow.objects.create(follower=self.alice, following=self.bob)
        self.assertContains(self.client.get(reverse("home")), "post from bob")

    def test_explore_shows_everything_and_paginates(self):
        for i in range(25):
            Post.objects.create(author=self.bob, content=f"post number {i}")
        response = self.client.get(reverse("explore"))
        self.assertContains(response, "post number 24")
        self.assertNotContains(response, "post number 0")
        self.assertContains(response, "before=")

    def test_like_toggle(self):
        post = Post.objects.create(author=self.bob, content="x")
        url = reverse("like_toggle", args=[post.pk])
        self.client.post(url)
        post.refresh_from_db()
        self.assertEqual(post.like_count, 1)
        self.assertTrue(Like.objects.filter(user=self.alice, post=post).exists())
        self.client.post(url)
        post.refresh_from_db()
        self.assertEqual(post.like_count, 0)
        self.assertFalse(Like.objects.exists())

    def test_repost_toggle(self):
        post = Post.objects.create(author=self.bob, content="x")
        url = reverse("repost_toggle", args=[post.pk])
        self.client.post(url)
        post.refresh_from_db()
        self.assertEqual(post.repost_count, 1)
        self.assertTrue(Post.objects.filter(author=self.alice, repost_of=post).exists())
        self.assertContains(self.client.get(reverse("home")), "You reposted")
        self.client.post(url)
        post.refresh_from_db()
        self.assertEqual(post.repost_count, 0)

    def test_reply_and_delete_update_parent_count(self):
        post = Post.objects.create(author=self.bob, content="parent")
        self.client.post(reverse("reply", args=[post.pk]), {"content": "a reply"})
        post.refresh_from_db()
        self.assertEqual(post.reply_count, 1)
        reply = Post.objects.get(parent=post)
        self.client.delete(reverse("delete_post", args=[reply.pk]))
        post.refresh_from_db()
        self.assertEqual(post.reply_count, 0)

    def test_cannot_delete_others_post(self):
        post = Post.objects.create(author=self.bob, content="x")
        self.assertEqual(self.client.delete(reverse("delete_post", args=[post.pk])).status_code, 404)

    def test_detail_page_shows_thread(self):
        root = Post.objects.create(author=self.bob, content="root post")
        child = Post.objects.create(author=self.alice, parent=root, content="child post")
        grandchild = Post.objects.create(author=self.bob, parent=child, content="grandchild post")
        response = self.client.get(reverse("post_detail", args=[grandchild.pk]))
        for text in ("root post", "child post", "grandchild post"):
            self.assertContains(response, text)

    def test_feed_updates_counts_then_shows_new_posts(self):
        Follow.objects.create(follower=self.alice, following=self.bob)
        first = Post.objects.create(author=self.bob, content="old post")
        url = reverse("feed_updates")
        self.assertNotContains(self.client.get(url, {"scope": "home", "since": first.pk}), "Show ")
        Post.objects.create(author=self.bob, content="brand new post")
        self.assertContains(self.client.get(url, {"scope": "home", "since": first.pk}), "Show 1 new post")
        response = self.client.get(url, {"scope": "home", "since": first.pk, "show": "1"})
        self.assertContains(response, "brand new post")
        self.assertContains(response, 'hx-swap-oob="true"')

    def test_feed_updates_thread_scope_counts_replies(self):
        root = Post.objects.create(author=self.bob, content="root")
        Post.objects.create(author=self.alice, parent=root, content="a reply")
        Post.objects.create(author=self.bob, parent=root, content="another reply")
        response = self.client.get(reverse("feed_updates"), {"scope": "thread", "post": root.pk, "since": 0})
        self.assertContains(response, "Show 2 new replies")

    def test_feed_updates_home_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("feed_updates"), {"scope": "home"}).status_code, 404)

    def test_detail_redirects_repost_to_original(self):
        post = Post.objects.create(author=self.bob, content="x")
        repost = Post.objects.create(author=self.alice, repost_of=post)
        self.assertRedirects(self.client.get(reverse("post_detail", args=[repost.pk])), post.get_absolute_url())
