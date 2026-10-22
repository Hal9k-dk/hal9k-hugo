<?php
// Only load WordPress's paragraph formatter; never bootstrap plugins or credentials.
require $argv[1] . '/wp-includes/formatting.php';
$contents = json_decode(stream_get_contents(STDIN), true, 512, JSON_THROW_ON_ERROR);
echo json_encode(array_map('wpautop', $contents), JSON_THROW_ON_ERROR | JSON_UNESCAPED_UNICODE);
