from types import SimpleNamespace

from specs.rendering import render_markdown

HOSTILE = (
    "![x](http://evil/p.png) see [docs](http://evil) <img src=http://evil/t.gif> http://evil/a"
)


def test_render_strips_images_links_html_and_urls():
    spec = SimpleNamespace(
        summary=HOSTILE,
        acceptance_criteria=[HOSTILE, "line one\n# heading"],
        implementation_steps=["<script>alert(1)</script>do it"],
        risks=[],
        out_of_scope=["www.evil.com"],
        size="M",
        prompt_version="spec-v1",
        model="m",
        issue_url="http://localhost:3000/blt/tasks/issues/1",
    )
    body = render_markdown(spec)
    generated, footer = body.split("---")
    assert "evil" not in generated
    assert "![" not in generated
    assert "<img" not in generated
    assert "<script" not in generated
    assert "## Summary\n\nsee docs" in generated
    assert "- line one # heading" in generated
    assert "- alert(1)do it" in generated
    assert "\n# heading" not in generated
    assert "http://localhost:3000/blt/tasks/issues/1" in footer
