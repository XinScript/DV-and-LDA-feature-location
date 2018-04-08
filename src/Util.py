from os import makedirs,path,walk
import Config

def make_dirs(target_path):

    makedirs(target_path) if not path.exists(target_path) else None

    map_path = path.join(target_path, 'Issue_Commit_Map.txt')

    log_path = path.join(target_path,'debug.txt')

    query_path = path.join(target_path, 'queries')
    makedirs(query_path) if not path.exists(query_path) else None

    goldset_class_path = path.join(target_path, 'goldsets', 'class')
    makedirs(goldset_class_path) if not path.exists(
        goldset_class_path) else None

    goldset_method_path = path.join(target_path, 'goldsets', 'method')
    makedirs(goldset_method_path) if not path.exists(
        goldset_method_path) else None

    d = {}
    d['query'] = query_path
    d['class'] = goldset_class_path
    d['method'] = goldset_method_path
    d['map'] = map_path
    d['log'] = log_path
    return d


def obj_binary_search(objs, field, target):
        if target < getattr(objs[0], field):
            return -1

        lo, hi = 0, len(objs) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if target < getattr(objs[mid], field):
                hi = mid - 1
            elif target > getattr(objs[mid], field):
                lo = mid + 1
            else:
                return mid
        return lo


    