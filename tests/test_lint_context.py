from groovescripting import lint


def ineffective_options(project):
    findings, _ = lint.lint_project(project)
    return [f["evidence"].get("option") for f in findings if f["rule_id"] == "PRJ003"]


def test_pulse_width_uses_preset_waveform_context():
    project = {
        "version": 1,
        "tracks": [
            {"name": "Bass", "instrument": "bass", "preset": "aggressive", "params": {"pulse_width": 0.2}}
        ],
    }
    assert ineffective_options(project) == []
    project["tracks"][0]["params"]["waveform"] = "saw"
    assert ineffective_options(project) == ["pulse_width"]


def test_ineffective_default_waveform_reports_only_explicit_options():
    project = {
        "version": 1,
        "tracks": [{"name": "Bass", "instrument": "bass", "params": {"pulse_width": 0.2}}],
    }
    findings, _ = lint.lint_project(project)
    ineffective = [f for f in findings if f["rule_id"] == "PRJ003"]
    assert len(ineffective) == 1
    assert ineffective[0]["location"] == "/tracks/0/params/pulse_width"
    assert ineffective[0]["evidence"] == {"option": "pulse_width", "value": 0.2}


def test_preset_without_explicit_modulators_has_no_default_findings():
    findings, _ = lint.lint_preset({"version": 1, "instrument": "lead", "params": {"waveform": "pulse"}})
    assert not [f for f in findings if f["rule_id"] == "PRJ003"]


def test_modulation_uses_preset_depth_and_voice_settings():
    project = {
        "version": 1,
        "tracks": [
            {"name": "Motion", "instrument": "lead", "preset": "experimental", "params": {"lfo_rate": 2}},
            {
                "name": "Wide",
                "instrument": "lead",
                "preset": "sustained",
                "params": {"vibrato_rate": 4, "unison_detune": 15},
            },
            {"name": "Filter", "instrument": "bass", "preset": "acid", "params": {"filter_attack": 0.1}},
        ],
    }
    assert ineffective_options(project) == []
    project["tracks"][0]["params"]["lfo_depth"] = 0
    project["tracks"][1]["params"].update(vibrato_depth=0, unison=1)
    project["tracks"][2]["params"]["filter_amount"] = 0
    assert ineffective_options(project) == ["lfo_rate", "vibrato_rate", "unison_detune", "filter_attack"]


def test_section_enabling_pulse_suppresses_global_ineffective_finding():
    project = {
        "version": 1,
        "tracks": [{"name": "Lead", "instrument": "lead", "params": {"pulse_width": 0.2}}],
        "sections": [{"bars": 1, "tracks": {"Lead": {"params": {"waveform": "pulse"}}}}],
    }
    assert ineffective_options(project) == []


def test_any_effective_section_suppresses_global_ineffective_finding():
    project = {
        "version": 1,
        "tracks": [{"name": "Lead", "instrument": "lead", "params": {"pulse_width": 0.2}}],
        "sections": [
            {"bars": 1},
            {"bars": 1, "tracks": {"Lead": {"preset": "experimental"}}},
        ],
    }
    assert ineffective_options(project) == []
    project["sections"][1]["tracks"]["Lead"]["params"] = {"waveform": "saw"}
    assert ineffective_options(project) == ["pulse_width"]
