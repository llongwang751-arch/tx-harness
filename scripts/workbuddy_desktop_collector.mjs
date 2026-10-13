// Native CUA observation/control receipt helper. Imported only in node_repl.
// All UI methods are documented native CUA methods; no alternate UI technology.
export function createCollector(app, evidence, fs, {initialIndex = 0} = {}) {
  if (!Number.isSafeInteger(initialIndex) || initialIndex < 0) {
    throw new RangeError('initialIndex must be a non-negative safe integer');
  }
  let index = initialIndex;
  async function record(label, observation) {
    const at = new Date().toISOString();
    const number = String(++index).padStart(3, '0');
    const ax = `${number}-${label}.ax.txt`;
    await fs.writeFile(`${evidence}/${ax}`, observation.state, 'utf8');
    const screenshot = observation.screenshot ? `${number}-${label}.png` : null;
    if (screenshot) await fs.writeFile(`${evidence}/${screenshot}`, observation.screenshot);
    await fs.appendFile(`${evidence}/capture-log.jsonl`, JSON.stringify({at,index,label,ax,screenshot})+'\n');
    return {at,index,label,state:observation.state};
  }
  async function observe(label, screenshots = true) {
    return record(label, screenshots ? await app.getAXStateAndScreenshot() :
      {state:await app.getAXState({emit:false})});
  }
  async function act(label, method, ...args) {
    if (!['click','paste','pressKey','scroll','performSecondaryAction'].includes(method)) throw new Error('Undocumented action');
    const at = new Date().toISOString();
    try {
      await app[method](...args);
      await fs.appendFile(`${evidence}/actions.jsonl`,JSON.stringify({at,label,method,args,result:'returned'})+'\n');
    } catch (error) {
      await fs.appendFile(`${evidence}/actions.jsonl`,JSON.stringify({at,label,method,args,result:'error',error:String(error.message)})+'\n');
      throw error;
    }
  }
  return {record,observe,act};
}
