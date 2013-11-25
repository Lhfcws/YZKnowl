#!/usr/bin/python
# -*- coding: utf-8 -*-
import re
import operator
import nltk
from scripts.algo import local_kw_ext
from scripts.model.model import Local_Model
from scripts.util import file_loader, kw_util, MyLib

__author__ = 'congzicun'


class fspair:
    def __init__(self):
        self.score = -1

    def set_pair(self, feature, sentiment, score):
        self.feature = feature
        self.sentiment = sentiment
        self.score = score

    def get_dis(self):
        if self.score != -1:
            return caldis(self.feature, self.sentiment)
        return 10000


def caldis(feature, sentiment):
    dis = abs(feature.wdpos - sentiment.wdpos)
    dis += 2 * abs(feature.phrspos - sentiment.phrspos)
    return dis


def slct_high_pmi(f_token, kws, pmi, kb):
    rstpair = fspair()

    for s_token in kws:
        if kb.instances.get(s_token.keyword, s_token.keyword) in kb.sentiments:
            tmp_pmi = pmi.get(f_token.origin + '$' + s_token.origin, 0)
            if tmp_pmi > rstpair.score or (tmp_pmi == rstpair.score and caldis(f_token, s_token) < rstpair.get_dis()):
                rstpair.set_pair(f_token, s_token, tmp_pmi)

    return rstpair


def feature_cmp(fs_pairs, tf_idf_scores):
    used_feature = set()
    used_sentiment = set()
    std_pairs = sorted(fs_pairs, key=operator.itemgetter(1), reverse=True)
    rst_pair = []
    for fs_pair, _ in std_pairs:
        if fs_pair.sentiment.origin not in used_sentiment:
            rst_pair.append(fs_pair)
            used_sentiment.add(fs_pair.sentiment.origin)
    return rst_pair


def load_mdl(infile):
    local_model = Local_Model()
    lns = [ln.decode('utf-8').lower().strip() for ln in open(infile).readlines()]
    feature_type = -1
    for ln in lns:
        if ln == '#FEATURE_SENTI_TYPE_DISTR'.lower():
            feature_type = 0
            continue
        elif ln == '#FEATURE_SENTI_DIST'.lower():
            feature_type = 1
            continue
        elif ln == '#AMBI_DIST'.lower():
            feature_type = 2
            continue
        elif ln == '#FEATURE_NULL'.lower():
            feature_type = 3
            continue
        elif ln == '#KW_DIS'.lower():
            feature_type = 4
            continue
        elif ln == '#TOTAL_DOC'.lower():
            feature_type = 5
            continue
        elif ln == '#CERTAIN_PAIR_DIS'.lower():
            feature_type = 6
            continue

        if feature_type == 0:
            kw1, kw2, dis_type, value = ln.strip().split('$')
            local_model.F_S_TYPE.setdefault(kw1 + '$' + kw2, nltk.FreqDist())
            local_model.F_S_TYPE[kw1 + '$' + kw2].inc(int(dis_type), float(value))
        elif feature_type == 1:
            kw1, kw2, value = ln.strip().split('$')
            local_model.FS_NUM[kw1 + '$' + kw2] = float(value)
            local_model.F_S_SET.setdefault(kw1, set())
            if kw2 != 'sentiment' and kw2 != 'feature':
                local_model.F_S_SET[kw1].add(kw2)
        elif feature_type == 2:
            sent_kw, not_amb_doc, total_doc = ln.strip().split('$')
            local_model.S_AMB[sent_kw] = float(not_amb_doc) / float(total_doc)
        elif feature_type == 3:
            feature, null_senti, total_doc = ln.strip().split('$')
            local_model.F_NULL[feature] = float(null_senti)
        elif feature_type == 4:
            kw, count = ln.strip().split('$')
            local_model.KW_DIS.inc(kw, float(count))
        elif feature_type == 5:
            total_null_doc, total_doc = ln.strip().split('$')
            local_model.TOTAL_NULL_SENTI = float(total_null_doc)
            local_model.TRAIN_SET_VOLUME = float(total_doc)
        elif feature_type == 6:
            feature, sentiment, count = ln.strip().split('$')
            local_model.CERNTAIN_PAIR.inc(feature + '$' + sentiment, float(count))
    return local_model


# def feature_cmp(fs_pairs):
#     used_feature = set()
#     used_sentiment = set()
#     std_pairs = sorted(fs_pairs, key=operator.itemgetter(1), reverse=True)
#     rst_pair = []
#     for fs_pair, _ in std_pairs:
#         if fs_pair.sentiment.origin not in used_sentiment:
#             rst_pair.append(fs_pair)
#             used_sentiment.add(fs_pair.sentiment.origin)
#     return rst_pair


def test2(filename, objname):
    dataset = file_loader.load_data_set(filename)
    dic = file_loader.load_dic()
    kb = file_loader.load_knw_base(objname)

    tf_idf_scores = local_kw_ext.extr_kw(dataset, kb, dic)
    pmi_scores = local_kw_ext.cal_pmi(dataset, dic)

    for tw in dataset:
        print tw.encode('utf-8')
        sentences = re.split(ur' ', kw_util.tweet_filter(kw_util.punc_replace(tw)))
        for sentence in sentences:
            rstpairs = []
            kw_tokens = MyLib.filter_sentiment(MyLib.seg_token(sentence, dic, kb), kb)
            for kw_token in kw_tokens:
                if MyLib.is_feature(kw_token, kb, objname):
                    tmp_fspair = slct_high_pmi(kw_token, kw_tokens, pmi_scores, kb)
                    if tmp_fspair.score != -1:
                        rstpairs.append((tmp_fspair, tf_idf_scores.get(tmp_fspair.feature.origin)))
                        # print 'tmp', tmp_fspair.feature.origin.encode('utf-8'), tmp_fspair.sentiment.origin.encode(
                        #     'utf-8'), tmp_fspair.score
            rstpairs = feature_cmp(rstpairs, tf_idf_scores)
            for pair in rstpairs:
                if pair.feature.keyword in kb.features:
                    print pair.feature.origin.encode('utf-8'), pair.sentiment.origin.encode('utf-8'), tf_idf_scores.get(
                        pair.feature.origin), tf_idf_scores.get(pair.sentiment.origin), pair.score


def cal_token_lkhd(token1, token2, local_model):
    feature = MyLib.dcd_ds_ftr_type(token1, token2)
    pair_name = token1.keyword + '$' + token2.keyword
    P_c_fs = 1
    if token1 is not token2:
        P_c_fs = P_c_fs * local_model.F_S_TYPE[pair_name].get(feature.word_dis) / local_model.FS_NUM[pair_name]
        P_c_fs = P_c_fs * local_model.F_S_TYPE[pair_name].get(feature.phrs_dis) / local_model.FS_NUM[pair_name]
        P_c_fs = P_c_fs * local_model.F_S_TYPE[pair_name].get(feature.rltv_dis) / local_model.FS_NUM[pair_name]

    pair_num = local_model.FS_NUM.get(pair_name, local_model.KW_DIS.get(token1.keyword)) - 1
    P_f_s = pair_num / local_model.TRAIN_SET_VOLUME

    likehd = P_c_fs * P_f_s
    #TODO:
    return likehd


def cal_f(tokenlst, kb, local_model, objname):
    objf_pair = [(obj_token, f_token)
                 for obj_token in tokenlst for f_token in tokenlst
                 if f_token.keyword in kb.features and obj_token.keyword == objname and obj_token is not f_token]
    f_score = {}
    for obj_token, f_token in objf_pair:
        lk_hd = cal_token_lkhd(obj_token, f_token, local_model)
        if f_score.get(f_token, 0) < lk_hd:
            f_score[f_token] = lk_hd
    return f_score


def cal_fs(f, tokenlst, kb, local_model):
    fs_pair = [(f, s) for s in tokenlst if s.keyword in kb.sentiments]
    fs_list = []
    for f_token, s_token in fs_pair:
        fs_score = cal_token_lkhd(f_token, s_token, local_model)
        fs_list.append((f_token, s_token, fs_score))
    return fs_list


def f_cmp(fs_lst):
    used_senti = set()
    std_fs_lst = sorted(fs_lst, key=operator.itemgetter(2), reverse=True)
    valid_pair = []
    for f, s, v in std_fs_lst:
        print '#', f.origin.encode('utf-8'), s.origin.encode('utf-8'), v
        if s not in used_senti:
            used_senti.add(s)
            valid_pair.append((f, s, v))
    return valid_pair


def test(file_name, obj_name, model_name):
    data_set = file_loader.load_data_set(file_name)
    dic = file_loader.load_dic()
    dic.add(obj_name)
    kb = file_loader.load_knw_base(obj_name)
    local_model = load_mdl(model_name)
    tfidf_scores = local_kw_ext.extr_kw(data_set, kb, dic)

    for tw in data_set:
        fspairlist = []
        sentences = re.split(ur'[!.?…~;"#:—]', kw_util.punc_replace(tw))
        for sen_index, sentence in enumerate(sentences):
            flist = {}
            if len(sentence.strip()) == 0:
                continue
            tokenlst = MyLib.filter_sentiment(MyLib.seg_token(sentence, dic, kb), kb)
            tokenlst = [token for token in tokenlst if token.keyword in kb.instances]
            f_score = cal_f(tokenlst, kb, local_model, obj_name)
            flist.update(f_score.items())
            tmp_fs_pair = []
            for f_token in flist.keys():
                tmp_fs_pair.extend(cal_fs(f_token, tokenlst, kb, local_model))
            fspairlist.extend(f_cmp(tmp_fs_pair))
        print tw.encode('utf-8').strip()
        for f, s, v in fspairlist:
            print f.origin.encode('utf-8'), s.origin.encode('utf-8'), v

