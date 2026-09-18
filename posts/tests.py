from django.test import SimpleTestCase, TestCase
from django.urls import reverse

from accounts.models import Follow, User

from .models import Bookmark, Like, Post
from .templatetags.feed_extras import linkify


class LinkifyTests(SimpleTestCase):
    def test_mentions_and_hashtags_become_links(self):
        html = linkify("hi @Bob check #django")
        self.assertIn('href="/@bob/"', html)
        self.assertIn('href="/tag/django/"', html)

    def test_escapes_html_and_keeps_entities_intact(self):
        html = linkify("<b>it's</b> #x")
        self.assertIn("&lt;b&gt;", html)
        self.assertIn("&#x27;", html)
        self.assertNotIn("/tag/x27/", html)
        self.assertIn('href="/tag/x/"', html)

    def test_email_is_not_a_mention(self):
        self.assertNotIn("href", linkify("mail me at bob@example.com"))

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

    def test_tag_page_lists_matching_posts_only(self):
        Post.objects.create(author=self.bob, content="love #django so much")
        Post.objects.create(author=self.bob, content="nothing here")
        Post.objects.create(author=self.bob, content="#djangonaut is different")
        response = self.client.get(reverse("tag", args=["django"]))
        self.assertContains(response, "love")
        self.assertNotContains(response, "nothing here")
        self.assertNotContains(response, "is different")

    def test_search_finds_people_and_posts(self):
        Post.objects.create(author=self.bob, content="the coroutines launch")
        self.assertContains(self.client.get(reverse("search"), {"q": "coroutines"}), "the coroutines launch")
        self.assertContains(self.client.get(reverse("search"), {"q": "bo"}), "@bob")

    def test_search_hashtag_redirects_to_tag(self):
        response = self.client.get(reverse("search"), {"q": "#django"})
        self.assertRedirects(response, reverse("tag", args=["django"]), fetch_redirect_response=False)

    def test_bookmark_toggle_and_page(self):
        post = Post.objects.create(author=self.bob, content="save me")
        url = reverse("bookmark_toggle", args=[post.pk])
        self.client.post(url)
        self.assertTrue(Bookmark.objects.filter(user=self.alice, post=post).exists())
        self.assertContains(self.client.get(reverse("bookmarks")), "save me")
        self.client.post(url)
        self.assertFalse(Bookmark.objects.exists())

    def test_bookmarks_requires_login(self):
        self.client.logout()
        self.assertEqual(self.client.get(reverse("bookmarks")).status_code, 302)

    def test_who_to_follow_excludes_self_and_followed(self):
        make_user("carol")
        Follow.objects.create(follower=self.alice, following=self.bob)
        response = self.client.get(reverse("explore"))
        self.assertContains(response, "Who to follow")
        self.assertContains(response, "@carol")
        self.assertNotContains(response, "@bob")

    def test_edit_post_by_author_only(self):
        post = Post.objects.create(author=self.alice, content="draft")
        response = self.client.post(reverse("edit_post", args=[post.pk]), {"content": "final"})
        self.assertRedirects(response, post.get_absolute_url())
        post.refresh_from_db()
        self.assertEqual(post.content, "final")
        self.assertIsNotNone(post.edited_at)
        self.assertContains(self.client.get(post.get_absolute_url()), "Edited")
        other = Post.objects.create(author=self.bob, content="not mine")
        self.assertEqual(self.client.get(reverse("edit_post", args=[other.pk])).status_code, 404)

    def test_posting_is_rate_limited(self):
        for i in range(10):
            Post.objects.create(author=self.alice, content=f"post {i}")
        self.assertEqual(self.client.post(reverse("compose"), {"content": "one more"}).status_code, 429)

    def test_trending_counts_recent_tags(self):
        Post.objects.create(author=self.bob, content="#django rocks")
        Post.objects.create(author=self.alice, content="more #Django here")
        response = self.client.get(reverse("explore"))
        self.assertContains(response, "Trending today")
        self.assertContains(response, "2 posts")

    def test_detail_redirects_repost_to_original(self):
        post = Post.objects.create(author=self.bob, content="x")
        repost = Post.objects.create(author=self.alice, repost_of=post)
        self.assertRedirects(self.client.get(reverse("post_detail", args=[repost.pk])), post.get_absolute_url())
