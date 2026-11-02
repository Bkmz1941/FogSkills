$SEND = getenv('SEND') === '1';
$IDS = getenv('IDS') ? array_map('intval', explode(',', getenv('IDS'))) : null;
$walk = function($v, $p, &$out) use (&$walk) { if (is_array($v)) { foreach ($v as $k => $x) $walk($x, "$p.$k", $out); } elseif (is_string($v) && str_contains($v, 'dlyamaster')) $out[] = "$p = " . substr($v, 0, 110); };
$rows = DB::table('application_settings as s')->join('applications as a','a.id','=','s.application_id')->where('s.content','like','%dlyamaster%')->orderBy('s.id')->get(['s.*','a.bundle_name']);
@mkdir(storage_path('app/backup-2026-10-31'), 0775, true);
foreach ($rows as $s) {
  $c = json_decode($s->content, true); $hits = []; $walk($c, '', $hits);
  echo "== {$s->id} {$s->bundle_name} {$s->project_id}/{$s->app_name}/{$s->name}\n"; foreach ($hits as $h) echo "     $h\n";
  if (!$SEND || ($IDS && !in_array($s->id, $IDS))) continue;
  file_put_contents(storage_path("app/backup-2026-10-31/application_settings-{$s->id}.json"), json_encode($s, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES));
  $raw = json_encode($c, JSON_UNESCAPED_UNICODE|JSON_UNESCAPED_SLASHES);
  $new = preg_replace('#https?://dlyamasterapoblokirovkam1?\.top#i', 'https://api2.ragnaros.top', $raw);
  if (str_contains($new, 'dlyamaster')) { echo "   SKIP: other dlyamaster host remains\n"; continue; }
  $p = ['name'=>$s->name,'project_id'=>$s->project_id,'app_name'=>$s->app_name,'content'=>$new];
  $k = $p; ksort($k); $vals = array_values($k); $vals[] = env('FB_SETTINGS_SECRET');
  $r = Http::timeout(30)->withHeaders(['X-FB-Token'=>md5(implode(';',$vals))])->acceptJson()->post('https://api3.ragnaros.net/api/firebase/settings', $p);
  echo "   POST: {$r->status()} " . substr($r->body(),0,150) . "\n";
}
