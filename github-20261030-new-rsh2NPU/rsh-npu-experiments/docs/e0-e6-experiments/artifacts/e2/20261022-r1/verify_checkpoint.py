"""Verify the sealed E2 failure checkpoint before extracting it locally."""
from pathlib import Path, PurePosixPath
import hashlib, json, sys, tarfile, struct
EXPECTED_SHA = 'db0dca9dd7811f7fae34ba569153bb0b84bfa55afe46eddaf2f13df8aa28e36f'
EXPECTED_SIZE = 5849507
EXPECTED_MEMBERS = 11265
archive = Path(sys.argv[1]).resolve()
target = Path(sys.argv[2]).resolve()
assert archive.stat().st_size == EXPECTED_SIZE, 'archive size mismatch'
assert hashlib.sha256(archive.read_bytes()).hexdigest() == EXPECTED_SHA, 'archive SHA mismatch'
assert not target.exists(), 'extraction target already exists'
with tarfile.open(archive, 'r:gz') as tf:
    members = tf.getmembers()
    names = [m.name for m in members]
    assert len(names) == EXPECTED_MEMBERS and len(set(names)) == len(names), 'member count/duplicates'
    for m in members:
        p = PurePosixPath(m.name)
        assert m.isfile() and not p.is_absolute() and '..' not in p.parts, 'unsafe archive member'
    manifest = json.load(tf.extractfile('checkpoint-member-sha256.json'))
    assert set(manifest) == set(names) - {'checkpoint-member-sha256.json'}, 'manifest coverage'
    for name, digest in manifest.items():
        assert hashlib.sha256(tf.extractfile(name).read()).hexdigest() == digest, f'member SHA: {name}'
    target.mkdir(parents=True)
    for m in members:
        p = target / m.name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(tf.extractfile(m).read())
        p.chmod(m.mode & 0o777)
record = {'status':'HASH_VERIFIED', 'archive':str(archive), 'sha256':EXPECTED_SHA,
          'bytes':EXPECTED_SIZE, 'members':len(names), 'member_hashes_verified':len(manifest),
          'extracted':str(target), 'device_experiment_pass':False,
          'note':'Preserves failed E2 smoke; hash verification does not establish device correctness.'}
(target.parent / 'local-checkpoint-verification.json').write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps(record,indent=2))
