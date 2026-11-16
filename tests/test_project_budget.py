import pytest

from groovescripting import projects


@pytest.mark.parametrize("sections", [None, [{"bars": 512, "repeat": 2}]])
def test_oversized_muted_arrangement_rejected_before_allocation(monkeypatch, sections):
    project = {
        "version": 1,
        "bars": 1024,
        "bpm": 1,
        "beats": 32,
        "sample_rate": 192000,
        "tracks": [{"name": "Muted", "instrument": "lead", "mute": True}],
    }
    if sections is not None:
        project["sections"] = sections

    def unexpected_allocation(*args, **kwargs):
        pytest.fail("oversized project attempted PCM allocation")

    monkeypatch.setattr(projects.np, "zeros", unexpected_allocation)
    with pytest.raises(ValueError, match="frames"):
        projects.render_project(project, unexpected_allocation)
