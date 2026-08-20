from services.video_extract import is_video_file


def test_is_video_file_by_extension_and_mime():
    assert is_video_file("asesor.mp4", None)
    assert is_video_file("asesor.MOV", "application/octet-stream")
    assert is_video_file("clip.bin", "video/webm")
    assert is_video_file("nota.wav", "audio/wav")
    assert not is_video_file("posei.pdf", "application/pdf")
    assert not is_video_file("ficha.md", "text/markdown")
