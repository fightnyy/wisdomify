from pytorch_lightning.callbacks import ModelCheckpoint
from torch.utils.data import DataLoader
from transformers import AutoModelForMaskedLM, AutoTokenizer
from wisdomify.datasets import WisdomDataset
from wisdomify.loaders import load_wisdom2def, load_conf, load_wisdom2eg
from wisdomify.models import RD
from wisdomify.builders import build_vocab2subwords
from wisdomify.paths import DATA_DIR
import pytorch_lightning as pl
import torch
import argparse
from wisdomify.vocab import VOCAB


def main():
    # --- setup the device --- #
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    # --- prep the arguments --- #
    parser = argparse.ArgumentParser()
    parser.add_argument("--exp", type=str,
                        default="a")
    args = parser.parse_args()
    exp: str = args.exp
    conf = load_conf()
    bert_model: str = conf['bert_model']
    data: str = conf['exps'][exp]['data']
    k: int = conf['exps'][exp]['k']
    lr: float = conf['exps'][exp]['lr']
    max_epochs: int = conf['exps'][exp]['max_epochs']
    batch_size: int = conf['exps'][exp]['batch_size']
    repeat: int = conf['exps'][exp]['repeat']
    num_workers: int = conf['exps'][exp]['num_workers']
    shuffle: bool = conf['exps'][exp]['shuffle']

    # --- the type of wisdomifier --- #
    if data == "wisdom2def":
        wisdom2sent = load_wisdom2def()
        model_name = "wisdomify_def_{epoch:02d}_{train_loss:.2f}"
    elif data == "wisdom2eg":
        wisdom2sent = load_wisdom2eg()
        model_name = "wisdomify_eg_{epoch:02d}_{train_loss:.2f}"
    else:
        raise NotImplementedError
    # --- instantiate the model --- #
    kcbert_mlm = AutoModelForMaskedLM.from_pretrained(bert_model)
    tokenizer = AutoTokenizer.from_pretrained(bert_model)
    dataset = WisdomDataset(wisdom2sent, tokenizer, k, VOCAB)
    dataset.upsample(repeat)  # just populate the batch
    vocab2subwords = build_vocab2subwords(tokenizer, k, VOCAB).to(device)
    rd = RD(kcbert_mlm, vocab2subwords, k, lr)  # mono rd
    rd.to(device)
    # --- setup a dataloader --- #
    dataloader = DataLoader(dataset, batch_size,
                            shuffle, num_workers=num_workers)
    # --- init callbacks --- #
    checkpoint_callback = ModelCheckpoint(
        monitor='train_loss',
        filename=model_name
    )
    # --- instantiate the trainer --- #
    trainer = pl.Trainer(gpus=torch.cuda.device_count(),
                         max_epochs=max_epochs,
                         callbacks=[checkpoint_callback],
                         default_root_dir=DATA_DIR)
    # --- start training --- #
    trainer.fit(model=rd,
                train_dataloader=dataloader)


if __name__ == '__main__':
    main()