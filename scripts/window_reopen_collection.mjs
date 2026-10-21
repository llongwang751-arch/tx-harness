// Local artifact custody only. Source paths must first be observed in native UI.
// This module does not control an application or inspect application internals.
export function createCollection({fs, crypto, performance, runDir, startMs}) {
  const receipts = [];
  const digest = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
  async function collect(label, sources) {
    const destination = `${runDir}/collected/${label}`;
    await fs.mkdir(destination, {recursive: true});
    for (const source of sources) {
      if (!source.scene || !source.name || /[\\/]/.test(source.name)) throw new Error('Need a reviewed UI source and plain filename');
      const before = await fs.readFile(source.path);
      const out = `${destination}/${source.name}`;
      await fs.writeFile(out, before, {flag:'wx'});
      const after = await fs.readFile(source.path);
      if (digest(before) !== digest(after)) throw new Error('Source changed during collection');
      const receipt = {at:new Date().toISOString(), elapsed_ms:performance.now()-startMs,
        source:source.path, scene:source.scene, collected:out,
        bytes:before.byteLength, sha256:digest(before)};
      receipts.push(receipt);
      await fs.appendFile(`${runDir}/collection.jsonl`, JSON.stringify(receipt)+'\n');
    }
    return receipts.slice(-sources.length);
  }
  async function seal(reason) {
    const at=new Date().toISOString(), elapsed_ms=performance.now()-startMs;
    const inventory=[];
    for (const receipt of receipts) {
      const bytes=await fs.readFile(receipt.collected);
      if (digest(bytes)!==receipt.sha256) throw new Error('Collected bytes changed before seal');
      inventory.push({...receipt});
    }
    const record={at,elapsed_ms,reason,budget_seconds:1200,
      within_budget:elapsed_ms<=1200000,inventory};
    await fs.writeFile(`${runDir}/seal.json`,JSON.stringify(record,null,2)+'\n',{flag:'wx'});
    return record;
  }
  return {collect,seal};
}
