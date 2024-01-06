from comfy.sd1_clip import SDTokenizer, escape_important, unescape_important, token_weights
from comfy.sd import CLIP


class CLIPSTATS(CLIP):
    def __init__(self, clip: CLIP):
        self.patcher = clip.patcher.clone()
        self.cond_stage_model = clip.cond_stage_model
        # self.tokenizer = SDTokenizerStats(clip.tokenizer) if isinstance(clip.tokenizer, SDTokenizer) else SDTokenizerStats(getattr(clip.tokenizer, clip.tokenizer.clip))
        self.tokenizer = clip.tokenizer
        self.layer_idx = clip.layer_idx

    def tokenize(self, text, return_word_ids=False):
        tokens, stats = self.tokenizer.tokenize_with_weights(text, return_word_ids)
        return tokens, stats


class SDTokenizerStats(SDTokenizer):
    def __init__(self, tokenizer: SDTokenizer) -> None:
        #def __init__(self, tokenizer_path=None, max_length=77, pad_with_end=True, embedding_directory=None, embedding_size=768, embedding_key='clip_l',
        #  tokenizer_class=CLIPTokenizer, has_start_token=True, pad_to_max_length=True):
        self.tokenizer = tokenizer.tokenizer
        self.max_length = tokenizer.max_length
        self.tokens_start = tokenizer.tokens_start
        self.start_token = tokenizer.start_token
        self.end_token = tokenizer.end_token
        self.pad_with_end = tokenizer.pad_with_end
        self.pad_to_max_length = tokenizer.pad_to_max_length
        self.inv_vocab = tokenizer.inv_vocab
        self.embedding_directory = tokenizer.embedding_directory
        self.max_word_length = tokenizer.max_word_length
        self.embedding_identifier = tokenizer.embedding_identifier
        self.embedding_size = tokenizer.embedding_size
        self.embedding_key = tokenizer.embedding_key

    def tokenize_with_weights(self, text:str, return_word_ids=False):
        '''
        Takes a prompt and converts it to a list of (token, weight, word id) elements.
        Tokens can both be integer tokens and pre computed CLIP tensors.
        Word id values are unique per word and embedding, where the id 0 is reserved for non word tokens.
        Returned list has the dimensions NxM where M is the input size of CLIP
        '''
        if self.pad_with_end:
            pad_token = self.end_token
        else:
            pad_token = 0

        text = escape_important(text)
        parsed_weights = token_weights(text, 1.0)

        print(f'parsed_weights {parsed_weights}')

        #tokenize words
        tokens = []
        words = []
        word_stats = {}
        for weighted_segment, weight in parsed_weights:
            print(f'weighted_segment [{weighted_segment}] weight [{weight}]')
            to_tokenize = unescape_important(weighted_segment).replace("\n", " ").split(' ')
            to_tokenize = [x for x in to_tokenize if x != ""]
            print(f'len words {len(to_tokenize)}', to_tokenize)
            for word in to_tokenize:
                #if we find an embedding, deal with the embedding
                if word.startswith(self.embedding_identifier) and self.embedding_directory is not None:
                    embedding_name = word[len(self.embedding_identifier):].strip('\n')
                    embed, leftover = self._try_get_embedding(embedding_name)
                    if embed is None:
                        print(f"warning, embedding:{embedding_name} does not exist, ignoring")
                    else:
                        if len(embed.shape) == 1:
                            tokens.append([(embed, weight)])
                        else:
                            tokens.append([(embed[x], weight) for x in range(embed.shape[0])])
                    #if we accidentally have leftover text, continue parsing using leftover, else move on to next word
                    if leftover != "":
                        word = leftover
                    else:
                        continue
                #parse word
                tokens.append([(t, weight) for t in self.tokenizer(word)["input_ids"][self.tokens_start:-1]])
                print(f'tokenize {word}: {self.tokenizer(word)}')
                word_stats[word] = { "num_tokens": len(self.tokenizer(word)['input_ids']) -2 }
                words.append(word)

        print(f'word stats: {word_stats}')

        #reshape token array to CLIP input size
        batched_tokens = []
        batch = []
        if self.start_token is not None:
            batch.append((self.start_token, 1.0, 0))
        batched_tokens.append(batch)
        token_stats = {}
        for i, t_group in enumerate(tokens):
            #determine if we're going to try and keep the tokens in a single batch
            is_large = len(t_group) >= self.max_word_length

            #print(f'i {i} t_group {t_group} is_large {is_large}')

            while len(t_group) > 0:
                if not f'batch{len(batched_tokens)}' in token_stats: token_stats[f'batch{len(batched_tokens)}'] = { 'words': [], 'num_tokens': 0 }
                if len(t_group) + len(batch) > self.max_length - 1:
                    remaining_length = self.max_length - len(batch) - 1
                    #break word in two and add end token
                    if is_large:
                        batch.extend([(t,w,i+1) for t,w in t_group[:remaining_length]])
                        for t,w in t_group[:remaining_length]: token_stats[f'batch{len(batched_tokens)}']['num_tokens'] += 1
                        batch.append((self.end_token, 1.0, 0))
                        t_group = t_group[remaining_length:]
                    #add end token and pad
                    else:
                        batch.append((self.end_token, 1.0, 0))
                        if self.pad_to_max_length:
                            batch.extend([(pad_token, 1.0, 0)] * (remaining_length))
                    print(f'creating new batch {len(batched_tokens)} done batch {batch}')
                    #start new batch
                    batch = []
                    if self.start_token is not None:
                        batch.append((self.start_token, 1.0, 0))
                    batched_tokens.append(batch)
                else:
                    batch.extend([(t,w,i+1) for t,w in t_group])
                    token_stats[f'batch{len(batched_tokens)}']['words'].append(words[i])
                    for t,w in t_group: token_stats[f'batch{len(batched_tokens)}']['num_tokens'] += 1
                    t_group = []

        #fill last batch
        batch.append((self.end_token, 1.0, 0))
        if self.pad_to_max_length:
            batch.extend([(pad_token, 1.0, 0)] * (self.max_length - len(batch)))

        if not return_word_ids:
            batched_tokens = [[(t, w) for t, w,_ in x] for x in batched_tokens]

        print(f'created {len(batched_tokens)} batches of tokens: {token_stats}')
        return batched_tokens, token_stats
